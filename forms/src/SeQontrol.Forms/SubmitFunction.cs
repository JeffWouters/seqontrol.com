using System.Net;
using System.Text;
using System.Text.Json;
using System.Web;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Extensions.Logging;

namespace SeQontrol.Forms;

public sealed record EndpointOptions
{
    /// <summary>Origins allowed to post, e.g. https://seqontrol.com. Compared exactly.</summary>
    public required IReadOnlySet<string> AllowedOrigins { get; init; }

    /// <summary>Where a browser without JavaScript is sent after a successful post.</summary>
    public required Uri ThanksUrl { get; init; }
}

/// <summary>POST /api/submit: the one endpoint every form on seqontrol.com posts to.</summary>
public sealed class SubmitFunction(SubmissionHandler handler, EndpointOptions endpoint, ILogger<SubmitFunction> log)
{
    // Far above any real enquiry (the message field caps at 5,000 characters), far below anything
    // that would cost money to read.
    internal const int MaxBodyBytes = 32 * 1024;

    [Function("submit")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "post", Route = "submit")] HttpRequestData req,
        CancellationToken ct)
    {
        var wantsJson = Header(req, "Accept").Contains("application/json", StringComparison.OrdinalIgnoreCase);

        // Browsers always send Origin on a cross-site POST, scripted or not. A request that carries a
        // foreign one was made from somebody else's page; one with none at all is a script, which the
        // honeypot and the field checks still have to get past.
        var origin = Header(req, "Origin");
        if (origin.Length > 0 && !endpoint.AllowedOrigins.Contains(origin))
        {
            log.LogWarning("Rejected a post from origin {Origin}", origin);
            return await Plain(req, HttpStatusCode.Forbidden, "Forbidden");
        }

        var contentType = Header(req, "Content-Type");
        if (!contentType.StartsWith("application/x-www-form-urlencoded", StringComparison.OrdinalIgnoreCase))
            return await Plain(req, HttpStatusCode.UnsupportedMediaType, "Send the form as application/x-www-form-urlencoded.");

        string body;
        try
        {
            body = await ReadCapped(req.Body, MaxBodyBytes, ct);
        }
        catch (InvalidDataException)
        {
            return await Plain(req, HttpStatusCode.RequestEntityTooLarge, "That is too long to be a form.");
        }

        HandlerResult result;
        try
        {
            result = await handler.HandleAsync(Parse(body), ct);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            log.LogError(ex, "A submission could not be stored");
            return wantsJson
                ? await Json(req, HttpStatusCode.InternalServerError, new { ok = false, errors = new[] { "That did not send." } })
                : await Page(req, HttpStatusCode.InternalServerError, "That did not send",
                    "Something went wrong at our end and your message was not stored. Go back, and either " +
                    "try again or email jeff@jeffops.com directly.");
        }

        if (result.Status == HandlerStatus.Invalid)
        {
            return wantsJson
                ? await Json(req, HttpStatusCode.BadRequest, new { ok = false, errors = result.Errors })
                : await Page(req, HttpStatusCode.BadRequest, "One more thing", string.Join(" ", result.Errors) +
                    " Go back to the form; what you typed is still there in most browsers.");
        }

        if (wantsJson)
            return await Json(req, HttpStatusCode.OK, new { ok = true });

        var redirect = req.CreateResponse(HttpStatusCode.SeeOther);
        redirect.Headers.Add("Location", endpoint.ThanksUrl.ToString());
        return redirect;
    }

    /// <summary>Form fields, last value wins. Keys are matched case-sensitively, as the forms send them.</summary>
    internal static Dictionary<string, string> Parse(string body)
    {
        var parsed = HttpUtility.ParseQueryString(body);
        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var key in parsed.AllKeys)
        {
            if (key is null) continue;
            var values = parsed.GetValues(key);
            fields[key] = values is { Length: > 0 } ? values[^1] : "";
        }
        return fields;
    }

    internal static async Task<string> ReadCapped(Stream body, int maxBytes, CancellationToken ct)
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[8192];
        int read;
        while ((read = await body.ReadAsync(chunk, ct)) > 0)
        {
            if (buffer.Length + read > maxBytes) throw new InvalidDataException("Body too large");
            buffer.Write(chunk, 0, read);
        }
        return Encoding.UTF8.GetString(buffer.GetBuffer(), 0, (int)buffer.Length);
    }

    private static string Header(HttpRequestData req, string name) =>
        req.Headers.TryGetValues(name, out var values) ? string.Join(",", values) : "";

    private static async Task<HttpResponseData> Json(HttpRequestData req, HttpStatusCode status, object payload)
    {
        var res = req.CreateResponse(status);
        res.Headers.Add("Content-Type", "application/json; charset=utf-8");
        res.Headers.Add("Cache-Control", "no-store");
        await res.WriteStringAsync(JsonSerializer.Serialize(payload));
        return res;
    }

    private static async Task<HttpResponseData> Plain(HttpRequestData req, HttpStatusCode status, string text)
    {
        var res = req.CreateResponse(status);
        res.Headers.Add("Content-Type", "text/plain; charset=utf-8");
        await res.WriteStringAsync(text);
        return res;
    }

    // Only reached by a browser posting without JavaScript, so it is deliberately bare: no styles, no
    // scripts, nothing the site's CSP would need to know about.
    private static async Task<HttpResponseData> Page(HttpRequestData req, HttpStatusCode status, string title, string text)
    {
        var res = req.CreateResponse(status);
        res.Headers.Add("Content-Type", "text/html; charset=utf-8");
        res.Headers.Add("Cache-Control", "no-store");
        var html = $"<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">" +
                   $"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">" +
                   $"<meta name=\"robots\" content=\"noindex\"><title>{WebUtility.HtmlEncode(title)} | SeQontrol</title>" +
                   $"<h1>{WebUtility.HtmlEncode(title)}</h1><p>{WebUtility.HtmlEncode(text)}</p>" +
                   "<p><a href=\"https://seqontrol.com/\">seqontrol.com</a></p></html>";
        await res.WriteStringAsync(html);
        return res;
    }
}
