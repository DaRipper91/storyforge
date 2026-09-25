using Godot;
using System;
using System.Text;

public partial class PythonClient : Node
{
    // Signals matching the original PythonClient.gd
    [Signal] public delegate void StateUpdatedEventHandler(Godot.Collections.Dictionary newState);
    [Signal] public delegate void NarrationReceivedEventHandler(string text);
    [Signal] public delegate void ConnectionStatusChangedEventHandler(bool connected);
    [Signal] public delegate void ParadoxTriggeredEventHandler(Godot.Collections.Array transformedIds);
    [Signal] public delegate void PhaseChangedEventHandler(string phase);
    [Signal] public delegate void NpcEventReceivedEventHandler(Godot.Collections.Dictionary ev);
    [Signal] public delegate void ParticleEventReceivedEventHandler(Godot.Collections.Dictionary ev);
    [Signal] public delegate void AuthCompletedEventHandler(bool success, Godot.Collections.Dictionary userInfo);
    [Signal] public delegate void CatalogReceivedEventHandler(Godot.Collections.Dictionary catalogData);
    [Signal] public delegate void CampaignsReceivedEventHandler(Godot.Collections.Array campaigns);
    [Signal] public delegate void NewCampaignReadyEventHandler(Godot.Collections.Dictionary state);
    [Signal] public delegate void CampaignLoadedEventHandler(Godot.Collections.Dictionary state);
    [Signal] public delegate void LobbyJoinedEventHandler(int slotIndex);
    [Signal] public delegate void CharacterCreatedEventHandler(Godot.Collections.Dictionary result);
    [Signal] public delegate void CharacterCreateFailedEventHandler(string error);
    [Signal] public delegate void GameStartedEventHandler();
    [Signal] public delegate void GameStartFailedEventHandler(string error);
    [Signal] public delegate void JonInventoryReceivedEventHandler(Godot.Collections.Array items);
    [Signal] public delegate void JonBuyResultEventHandler(bool success, string message);

    private const string ConfigPath = "user://settings.cfg";
    private const string ConfigSection = "network";
    private const string ConfigKeyUrl = "server_url";
    private const string DefaultUrl = "http://127.0.0.1:8765";

    [Export]
    public string server_url = DefaultUrl;

    public bool is_connected = false;

    private WebSocketPeer ws_client = new WebSocketPeer();

    private string _base_url => server_url.TrimEnd('/') + "/api";

    private string _ws_url
    {
        get
        {
            string baseStr = server_url.TrimEnd('/');
            if (baseStr.StartsWith("https://"))
            {
                baseStr = "wss://" + baseStr.Substring(8);
            }
            else if (baseStr.StartsWith("http://"))
            {
                baseStr = "ws://" + baseStr.Substring(7);
            }
            return baseStr + "/ws/session/main";
        }
    }

    public override void _Ready()
    {
        _setup_input_map();
    }

    private void _setup_input_map()
    {
        var actions = new Godot.Collections.Dictionary<string, Godot.Collections.Array>
        {
            { "move_up", new Godot.Collections.Array { (int)Key.W, (int)Key.Up, new Godot.Collections.Array { (int)JoyAxis.LeftY, -1.0f } } },
            { "move_down", new Godot.Collections.Array { (int)Key.S, (int)Key.Down, new Godot.Collections.Array { (int)JoyAxis.LeftY, 1.0f } } },
            { "move_left", new Godot.Collections.Array { (int)Key.A, (int)Key.Left, new Godot.Collections.Array { (int)JoyAxis.LeftX, -1.0f } } },
            { "move_right", new Godot.Collections.Array { (int)Key.D, (int)Key.Right, new Godot.Collections.Array { (int)JoyAxis.LeftX, 1.0f } } },
            { "action", new Godot.Collections.Array { (int)Key.E, (int)Key.Enter, (int)JoyButton.A } },
            { "lock_on", new Godot.Collections.Array { (int)Key.Q, new Godot.Collections.Array { (int)JoyAxis.TriggerLeft, 1.0f } } },
            { "freeform", new Godot.Collections.Array { (int)Key.F, new Godot.Collections.Array { (int)JoyAxis.TriggerRight, 1.0f } } },
            { "map", new Godot.Collections.Array { (int)Key.M, (int)JoyButton.Back } },
            { "reset_cam", new Godot.Collections.Array { (int)Key.R, (int)JoyButton.Start } },
            { "cycle_prev", new Godot.Collections.Array { (int)JoyButton.DpadLeft } },
            { "cycle_next", new Godot.Collections.Array { (int)Key.Tab, (int)JoyButton.DpadRight } },
            { "look_up", new Godot.Collections.Array { new Godot.Collections.Array { (int)JoyAxis.RightY, -1.0f } } },
            { "look_down", new Godot.Collections.Array { new Godot.Collections.Array { (int)JoyAxis.RightY, 1.0f } } },
            { "look_left", new Godot.Collections.Array { new Godot.Collections.Array { (int)JoyAxis.RightX, -1.0f } } },
            { "look_right", new Godot.Collections.Array { new Godot.Collections.Array { (int)JoyAxis.RightX, 1.0f } } }
        };

        foreach (var pair in actions)
        {
            string action = pair.Key;
            if (!InputMap.HasAction(action))
            {
                InputMap.AddAction(action);
            }

            foreach (var eventData in pair.Value)
            {
                InputEvent ev = null;
                if (eventData.VariantType == Variant.Type.Int)
                {
                    int val = eventData.AsInt32();
                    if (val < 500) // Simple heuristic for JoyButton vs KeyCode
                    {
                        var joyEvent = new InputEventJoypadButton();
                        joyEvent.ButtonIndex = (JoyButton)val;
                        ev = joyEvent;
                    }
                    else
                    {
                        var keyEvent = new InputEventKey();
                        keyEvent.PhysicalKeycode = (Key)val;
                        ev = keyEvent;
                    }
                }
                else if (eventData.VariantType == Variant.Type.Array)
                {
                    var arr = eventData.AsGodotArray();
                    var joyMotionEvent = new InputEventJoypadMotion();
                    joyMotionEvent.Axis = (JoyAxis)arr[0].AsInt32();
                    joyMotionEvent.AxisValue = arr[1].AsSingle();
                    ev = joyMotionEvent;
                }

                if (ev != null)
                {
                    InputMap.ActionAddEvent(action, ev);
                }
            }
        }
    }

    public void start_connection(string url)
    {
        server_url = url.TrimEnd('/');
        _save_url(server_url);
        check_python_server();
    }

    public string load_saved_url()
    {
        var cfg = new ConfigFile();
        if (cfg.Load(ConfigPath) == Error.Ok)
        {
            return cfg.GetValue(ConfigSection, ConfigKeyUrl, DefaultUrl).AsString();
        }
        return DefaultUrl;
    }

    private void _save_url(string url)
    {
        var cfg = new ConfigFile();
        cfg.Load(ConfigPath);
        cfg.SetValue(ConfigSection, ConfigKeyUrl, url);
        cfg.Save(ConfigPath);
    }

    public void check_python_server()
    {
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                is_connected = true;
                EmitSignal(SignalName.ConnectionStatusChanged, true);
                connect_websocket();
            }
            else
            {
                is_connected = false;
                EmitSignal(SignalName.ConnectionStatusChanged, false);
                GetTree().CreateTimer(2.0).Timeout += check_python_server;
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/healthz");
    }

    public void connect_websocket()
    {
        ws_client.ConnectToUrl(_ws_url);
    }

    public override void _Process(double delta)
    {
        ws_client.Poll();
        var state = ws_client.GetReadyState();
        if (state == WebSocketPeer.State.Open)
        {
            while (ws_client.GetAvailablePacketCount() > 0)
            {
                var packet = ws_client.GetPacket();
                string jsonStr = Encoding.UTF8.GetString(packet);
                _handle_ws_message(jsonStr);
            }
        }
        else if (state == WebSocketPeer.State.Closed)
        {
            // Optional reconnect logic could go here
        }
    }

    private void _handle_ws_message(string jsonStr)
    {
        var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
        if (json != null && json.ContainsKey("type"))
        {
            string type = json["type"].AsString();
            switch (type)
            {
                case "state_diff":
                    fetch_full_state();
                    break;
                case "narration":
                    EmitSignal(SignalName.NarrationReceived, json["text"].AsString());
                    break;
                case "paradox_triggered":
                    EmitSignal(SignalName.ParadoxTriggered, json.ContainsKey("transformed_ids") ? json["transformed_ids"].AsGodotArray() : new Godot.Collections.Array());
                    break;
                case "phase_changed":
                    EmitSignal(SignalName.PhaseChanged, json.ContainsKey("phase") ? json["phase"].AsString() : "");
                    break;
                case "npc_event":
                    _handle_npc_event(json);
                    EmitSignal(SignalName.NpcEventReceived, json);
                    break;
                case "particle_event":
                    EmitSignal(SignalName.ParticleEventReceived, json);
                    break;
            }
        }
    }

    private void _handle_npc_event(Godot.Collections.Dictionary ev)
    {
        string npc = ev.ContainsKey("npc") ? ev["npc"].AsString() : "";
        string action = ev.ContainsKey("action") ? ev["action"].AsString() : "";
        string mood = ev.ContainsKey("mood") ? ev["mood"].AsString() : "warm";

        if (npc == "redvelvet" && action == "perform")
        {
            string path = $"res://assets/audio/performance_{mood}.wav";
            var audioManager = GetNode("/root/AudioManager");
            audioManager.Call("play_npc_performance", path, mood);
        }
    }

    public void fetch_full_state()
    {
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            var jsonStr = Encoding.UTF8.GetString(body);
            var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
            if (json != null)
            {
                EmitSignal(SignalName.StateUpdated, json);
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/state");
    }

    public HttpRequest post_request(string endpoint, Godot.Collections.Dictionary data)
    {
        var http = new HttpRequest();
        AddChild(http);
        string jsonData = Json.Stringify(data);
        string[] headers = new string[] { "Content-Type: application/json" };
        http.Request(_base_url + endpoint, headers, HttpClient.Method.Post, jsonData);
        return http;
    }

    public HttpRequest get_request(string endpoint)
    {
        var http = new HttpRequest();
        AddChild(http);
        http.Request(_base_url + endpoint);
        return http;
    }

    public void trigger_desktop_login()
    {
        GD.Print("Triggering Desktop Auth flow...");
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            var jsonStr = Encoding.UTF8.GetString(body);
            var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
            if (responseCode == 200 && json != null && json.ContainsKey("status") && json["status"].AsString() == "ok")
            {
                var user = json.ContainsKey("user") ? json["user"].AsGodotDictionary() : new Godot.Collections.Dictionary();
                GD.Print("Auth successful! User: ", user.ContainsKey("name") ? user["name"].AsString() : "Unknown");
                EmitSignal(SignalName.AuthCompleted, true, user);
            }
            else
            {
                GD.Print("Auth failed or was cancelled.");
                EmitSignal(SignalName.AuthCompleted, false, new Godot.Collections.Dictionary());
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/auth/desktop_login", new string[] { }, HttpClient.Method.Post, "");
    }

    public HttpRequest fetch_catalog()
    {
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null)
                {
                    EmitSignal(SignalName.CatalogReceived, json);
                }
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/lobby/catalog");
        return http;
    }

    public void fetch_campaigns()
    {
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null && json.ContainsKey("campaigns"))
                {
                    EmitSignal(SignalName.CampaignsReceived, json["campaigns"].AsGodotArray());
                }
                else
                {
                    EmitSignal(SignalName.CampaignsReceived, new Godot.Collections.Array());
                }
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/campaigns");
    }

    public void new_campaign()
    {
        var http = new HttpRequest();
        AddChild(http);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null)
                {
                    EmitSignal(SignalName.NewCampaignReady, json);
                }
            }
            http.QueueFree();
        };
        http.Request(_base_url + "/campaigns/new", new string[] { }, HttpClient.Method.Post, "");
    }

    public void load_campaign(string campaignId)
    {
        var data = new Godot.Collections.Dictionary { { "campaign_id", campaignId } };
        var http = post_request("/campaigns/load", data);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null)
                {
                    EmitSignal(SignalName.CampaignLoaded, json);
                }
            }
            http.QueueFree();
        };
    }

    public void join_lobby(string controllerId)
    {
        var data = new Godot.Collections.Dictionary { { "controller_id", controllerId } };
        var http = post_request("/lobby/join", data);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null)
                {
                    EmitSignal(SignalName.LobbyJoined, json.ContainsKey("slot_index") ? json["slot_index"].AsInt32() : 0);
                }
            }
            http.QueueFree();
        };
    }

    public void set_phase(string phase)
    {
        var data = new Godot.Collections.Dictionary { { "phase", phase } };
        var http = post_request("/lobby/set_phase", data);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            http.QueueFree();
        };
    }

    public void create_character(Godot.Collections.Dictionary data)
    {
        var http = post_request("/character/create", data);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            var jsonStr = Encoding.UTF8.GetString(body);
            var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
            if (responseCode == 200 && json != null)
            {
                EmitSignal(SignalName.CharacterCreated, json);
            }
            else
            {
                string msg = json != null && json.ContainsKey("detail") ? json["detail"].AsString() : "Unknown error";
                EmitSignal(SignalName.CharacterCreateFailed, msg);
            }
            http.QueueFree();
        };
    }

    public void start_game()
    {
        var http = post_request("/lobby/start", new Godot.Collections.Dictionary());
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode == 200)
            {
                EmitSignal(SignalName.GameStarted);
            }
            else
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                string msg = json != null && json.ContainsKey("detail") ? json["detail"].AsString() : "Unknown error";
                EmitSignal(SignalName.GameStartFailed, msg);
            }
            http.QueueFree();
        };
    }

    public void fetch_jon_inventory(string genre = "fantasy")
    {
        var http = get_request("/npc/jon/inventory?genre=" + genre);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            if (responseCode != 200)
            {
                EmitSignal(SignalName.JonInventoryReceived, new Godot.Collections.Array());
            }
            else
            {
                var jsonStr = Encoding.UTF8.GetString(body);
                var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
                if (json != null && json.ContainsKey("items"))
                {
                    EmitSignal(SignalName.JonInventoryReceived, json["items"].AsGodotArray());
                }
                else
                {
                    EmitSignal(SignalName.JonInventoryReceived, new Godot.Collections.Array());
                }
            }
            http.QueueFree();
        };
    }

    public void buy_jon_item(string actorId, string itemId, string genre = "fantasy")
    {
        var data = new Godot.Collections.Dictionary
        {
            { "actor_id", actorId },
            { "item_id", itemId },
            { "genre", genre }
        };
        var http = post_request("/npc/jon/buy", data);
        http.RequestCompleted += (result, responseCode, headers, body) =>
        {
            var jsonStr = Encoding.UTF8.GetString(body);
            var json = (Godot.Collections.Dictionary)Json.ParseString(jsonStr);
            if (responseCode == 200)
            {
                string msg = json != null && json.ContainsKey("message") ? json["message"].AsString() : "Purchased!";
                EmitSignal(SignalName.JonBuyResult, true, msg);
            }
            else
            {
                string msg = json != null && json.ContainsKey("detail") ? json["detail"].AsString() : "Purchase failed.";
                EmitSignal(SignalName.JonBuyResult, false, msg);
            }
            http.QueueFree();
        };
    }
}
