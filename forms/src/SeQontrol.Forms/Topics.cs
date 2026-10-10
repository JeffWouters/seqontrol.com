namespace SeQontrol.Forms;

/// <summary>
/// The topics the site's forms can send, and the wording the acknowledgement uses for each.
/// </summary>
/// <remarks>
/// The acknowledgement goes to whatever address was typed into a public form, so it must never carry
/// text the sender chose: otherwise the form is a free way to send any message, from our domain, to
/// anyone. The topic arrives from a select box but is still sender-controlled, so it is only ever
/// used as a key into this table. Anything not in it is acknowledged as "your message".
/// Keep the keys in step with the &lt;option&gt; text on contact.html and the form topics in
/// tools/build_legal.py.
/// </remarks>
public static class Topics
{
    private static readonly Dictionary<string, string> Phrases = new(StringComparer.Ordinal)
    {
        ["A walkthrough of the platform"] = "a walkthrough of the platform",
        ["A scoped assessment (Copilot oversharing)"] = "a scoped Copilot-oversharing assessment",
        ["A scoped assessment (email spoofing / DMARC)"] = "a scoped email-spoofing assessment",
        ["A security posture assessment"] = "a security posture assessment",
        ["A compliance readiness snapshot"] = "a compliance readiness snapshot",
        ["Partner / MSP model"] = "the partner model",
        ["A quote for my estate"] = "a quote for your estate",
        ["Pricing for my estate"] = "a price for your estate",
        ["Free spoofing / DMARC check"] = "a free spoofing check",
        ["Free public surface scan"] = "a free surface scan",
        ["Free exposure report"] = "a free exposure report",
        ["Tell me when ConditionalAccessPortal ships"] = "hearing when ConditionalAccessPortal ships",
        ["Tell me when CompliancePortal ships"] = "hearing when CompliancePortal ships",
        ["Tell me when PosturePortal ships"] = "hearing when PosturePortal ships",
        ["Tell me when Dredd ships"] = "hearing when Dredd ships",
        ["Something else"] = "your message",
    };

    /// <summary>The acknowledgement's wording for a topic: a fixed phrase, never the input itself.</summary>
    public static string Phrase(string topic) =>
        Phrases.TryGetValue(topic, out var phrase) ? phrase : "your message";

    public static bool IsKnown(string topic) => Phrases.ContainsKey(topic);

    public static IReadOnlyCollection<string> All => Phrases.Keys;
}
