using Godot;
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public partial class PythonClientAsync : RichTextLabel
{
    // The endpoint to POST to. Defaults to the local StoryForge freeform action API.
    [Export]
    public string ServerUrl { get; set; } = "http://127.0.0.1:8765/api/action/freeform";

    // Reuse a single HttpClient instance across requests to avoid socket exhaustion
    private static readonly System.Net.Http.HttpClient _httpClient = new System.Net.Http.HttpClient();

    public override void _Ready()
    {
        // Initial setup/placeholder text
        BbcodeEnabled = true;
        Text = "[color=yellow]System Online.[/color] Waiting for narrative action...";
    }

    /// <summary>
    /// Asynchronously sends the player's freeform text action to the Python backend
    /// and updates the RichTextLabel with the response or error details.
    /// </summary>
    /// <param name="actionText">The raw action input from the user/player.</param>
    public async Task SendActionAsync(string actionText)
    {
        Text = "[color=cyan]Sending action to the story engine...[/color]";

        try
        {
            // Construct the payload. In StoryForge, player actions are JSON objects.
            var payload = new
            {
                text = actionText
            };

            string jsonPayload = JsonSerializer.Serialize(payload);
            var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            // Perform the non-blocking POST request
            HttpResponseMessage response = await _httpClient.PostAsync(ServerUrl, content);

            // Read response content asynchronously
            string responseBody = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
            {
                // Format and display the successful response
                // Since this runs on the Godot main thread loop via the task scheduler awaiter,
                // it is safe to interact directly with UI nodes here.
                Text = responseBody;
            }
            else
            {
                // Display error response codes or server failures
                Text = $"[color=red]Error (Status {(int)response.StatusCode}):[/color] {response.ReasonPhrase}\n\n{responseBody}";
            }
        }
        catch (HttpRequestException ex)
        {
            GD.PrintErr($"StoryForge Connection Exception: {ex.Message}");
            Text = "[color=red]Connection Error:[/color] Could not connect to the Python story server. Make sure the backend is running.";
        }
        catch (Exception ex)
        {
            GD.PrintErr($"Unexpected Exception in PythonClientAsync: {ex.Message}");
            Text = $"[color=red]Unexpected Error:[/color] {ex.Message}";
        }
    }
}
