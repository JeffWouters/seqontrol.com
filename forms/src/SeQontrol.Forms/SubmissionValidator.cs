using System.Net.Mail;
using System.Text;

namespace SeQontrol.Forms;

/// <summary>Turns the raw fields of a posted form into a <see cref="Submission"/>, or says why not.</summary>
public static class SubmissionValidator
{
    /// <summary>The trap field. It is hidden from people and left empty by them; bots fill it in.</summary>
    public const string HoneypotField = "website";

    /// <summary>Milliseconds since the epoch at which site.js saw the form render.</summary>
    public const string RenderedAtField = "ts";

    /// <summary>A person cannot read the form and fill in a name and an address in less than this.</summary>
    public static readonly TimeSpan MinimumFillTime = TimeSpan.FromSeconds(3);

    public static readonly string[] UtmFields =
        ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];

    // Caps, not targets. Generous enough that nobody writing a real enquiry meets one, tight enough
    // that the table and the notification mail stay a sensible size whatever is thrown at them.
    internal const int NameMax = 200;
    internal const int EmailMax = 254;   // RFC 5321 path limit
    internal const int OrganisationMax = 200;
    internal const int TopicMax = 200;
    internal const int EstateMax = 500;
    internal const int MessageMax = 5000;
    internal const int PageMax = 500;
    internal const int UtmMax = 200;

    public static ValidationOutcome Validate(IReadOnlyDictionary<string, string> fields, DateTimeOffset now)
    {
        string Get(string key) => fields.TryGetValue(key, out var v) ? v : "";

        // Spam checks first, and silently: a bot that is told why it failed tries again differently.
        if (Get(HoneypotField).Trim().Length > 0)
            return new ValidationOutcome.Spam("honeypot");

        // Only present when JavaScript ran. A form posted without it (no-JS) is not penalised for
        // its absence; a timestamp that is present and says "three seconds ago or less" is a script.
        if (long.TryParse(Get(RenderedAtField), out var renderedMs))
        {
            var rendered = DateTimeOffset.FromUnixTimeMilliseconds(Math.Clamp(renderedMs, 0, 253402300799999));
            var elapsed = now - rendered;
            if (elapsed >= TimeSpan.Zero && elapsed < MinimumFillTime)
                return new ValidationOutcome.Spam("too-fast");
        }

        var errors = new List<string>();

        var name = SingleLine(Get("name"), NameMax);
        if (name.Length == 0) errors.Add("A name helps.");

        var email = SingleLine(Get("email"), EmailMax + 1);
        if (email.Length == 0) errors.Add("We need an email address to reply to.");
        else if (email.Length > EmailMax || !LooksLikeEmail(email)) errors.Add("That email address does not look right.");

        if (errors.Count > 0)
            return new ValidationOutcome.Invalid(errors);

        var utm = new Dictionary<string, string>();
        foreach (var key in UtmFields)
        {
            var value = SingleLine(Get(key), UtmMax);
            if (value.Length > 0) utm[key] = value;
        }

        return new ValidationOutcome.Valid(new Submission(
            Topic: SingleLine(Get("topic"), TopicMax),
            Name: name,
            Email: email,
            Organisation: SingleLine(Get("org"), OrganisationMax),
            Estate: SingleLine(Get("estate"), EstateMax),
            Message: MultiLine(Get("message"), MessageMax),
            Page: SingleLine(Get("page"), PageMax),
            Referrer: SingleLine(Get("referrer"), PageMax),
            Utm: utm,
            ReceivedUtc: now));
    }

    internal static bool LooksLikeEmail(string value)
    {
        // MailAddress accepts display-name forms ("Jeff <jeff@example.com>") and a few other shapes
        // nobody types into an email field; requiring the parsed address to equal the input rejects
        // them. A dot in the domain rejects "jeff@localhost", which is never a reply address here.
        if (value.Contains(' ') || value.Contains('<') || value.Contains(',')) return false;
        if (!MailAddress.TryCreate(value, out var parsed)) return false;
        return string.Equals(parsed.Address, value, StringComparison.OrdinalIgnoreCase)
               && parsed.Host.Contains('.')
               && !parsed.Host.StartsWith('.') && !parsed.Host.EndsWith('.');
    }

    /// <summary>Trims, removes every control character (newlines included) and caps the length.</summary>
    internal static string SingleLine(string value, int max)
    {
        var sb = new StringBuilder(Math.Min(value.Length, max));
        foreach (var c in value)
        {
            if (char.IsControl(c)) { sb.Append(' '); continue; }
            sb.Append(c);
        }
        return Cap(CollapseSpaces(sb.ToString()).Trim(), max);
    }

    /// <summary>Like <see cref="SingleLine"/>, but keeps line breaks, normalised to \n.</summary>
    internal static string MultiLine(string value, int max)
    {
        var normalised = value.Replace("\r\n", "\n").Replace('\r', '\n');
        var sb = new StringBuilder(Math.Min(normalised.Length, max));
        foreach (var c in normalised)
        {
            if (c == '\n' || c == '\t') { sb.Append(c); continue; }
            if (char.IsControl(c)) continue;
            sb.Append(c);
        }
        return Cap(sb.ToString().Trim(), max);
    }

    private static string CollapseSpaces(string value)
    {
        var sb = new StringBuilder(value.Length);
        var lastWasSpace = false;
        foreach (var c in value)
        {
            var isSpace = c == ' ';
            if (isSpace && lastWasSpace) continue;
            sb.Append(c);
            lastWasSpace = isSpace;
        }
        return sb.ToString();
    }

    // Caps on a text-element boundary so a cap never splits a surrogate pair into invalid UTF-16.
    private static string Cap(string value, int max)
    {
        if (value.Length <= max) return value;
        var cut = max;
        if (char.IsHighSurrogate(value[cut - 1])) cut--;
        return value[..cut];
    }
}
