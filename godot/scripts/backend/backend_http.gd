class_name BackendHttp
extends Node
## Drop-in stand-in for HTTPRequest that answers from an in-process GameBackend.
##
## Same `request_completed(result, response_code, headers, body: PackedByteArray)` signal and a compatible
## `request(url, custom_headers, method, request_data) -> int`, so call sites that build their own
## HTTPRequest keep working unchanged (see PythonClient.new_http()).
##
## The completion is emitted on the NEXT frame, like a real network request, so callers that connect
## `request_completed` after calling `request()` still receive it. The node frees itself afterwards
## (callers' own `queue_free()` on it is harmless).

signal request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray)

var backend: GameBackend = null

const _METHODS := {
	HTTPClient.METHOD_GET: "GET",
	HTTPClient.METHOD_POST: "POST",
	HTTPClient.METHOD_PUT: "PUT",
	HTTPClient.METHOD_DELETE: "DELETE",
	HTTPClient.METHOD_PATCH: "PATCH",
	HTTPClient.METHOD_HEAD: "HEAD",
	HTTPClient.METHOD_OPTIONS: "OPTIONS",
}


func request(url: String, _custom_headers: PackedStringArray = PackedStringArray(),
		method: int = HTTPClient.METHOD_GET, request_data: String = "") -> int:
	if backend == null:
		return ERR_UNCONFIGURED
	var path := _strip_origin(url)
	var query := {}
	var qi := path.find("?")
	if qi >= 0:
		query = _parse_query(path.substr(qi + 1))
		path = path.substr(0, qi)
	var body := {}
	if request_data.strip_edges() != "":
		var parsed: Variant = JSON.parse_string(request_data)
		if parsed is Dictionary:
			body = parsed
	var resp: Dictionary = backend.request(_METHODS.get(method, "GET"), path, body, query)
	_complete.call_deferred(resp)
	return OK


## "http://host:port/api/x?y" -> "/api/x?y" (already-relative paths are kept).
static func _strip_origin(url: String) -> String:
	var si := url.find("://")
	if si < 0:
		return url if url.begins_with("/") else "/" + url
	var slash := url.find("/", si + 3)
	return "/" if slash < 0 else url.substr(slash)


static func _parse_query(qs: String) -> Dictionary:
	var out := {}
	for pair in qs.split("&", false):
		var kv := pair.split("=", true, 1)
		out[kv[0].uri_decode()] = kv[1].uri_decode() if kv.size() > 1 else ""
	return out


static func encode_body(body: Variant) -> PackedByteArray:
	if body is String:
		return (body as String).to_utf8_buffer()
	return JSON.stringify(body).to_utf8_buffer()


func _complete(resp: Dictionary) -> void:
	var tree := Engine.get_main_loop() as SceneTree
	if tree != null:
		await tree.process_frame
	if not is_instance_valid(self):
		return
	request_completed.emit(HTTPRequest.RESULT_SUCCESS, int(resp.get("status", 500)),
		PackedStringArray(), encode_body(resp.get("body", {})))
	if is_instance_valid(self) and not is_queued_for_deletion():
		queue_free()
