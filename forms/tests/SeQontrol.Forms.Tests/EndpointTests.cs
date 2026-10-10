using System.Text;
using SeQontrol.Forms;
using Xunit;

namespace SeQontrol.Forms.Tests;

public class EndpointTests
{
    [Fact]
    public void Form_bodies_parse_with_the_last_value_winning()
    {
        var fields = SubmitFunction.Parse("name=Jeff+W&email=a%40b.com&name=Second&empty=");
        Assert.Equal("Second", fields["name"]);
        Assert.Equal("a@b.com", fields["email"]);
        Assert.Equal("", fields["empty"]);
    }

    [Fact]
    public async Task Bodies_over_the_cap_are_refused()
    {
        using var big = new MemoryStream(new byte[SubmitFunction.MaxBodyBytes + 1]);
        await Assert.ThrowsAsync<InvalidDataException>(() => SubmitFunction.ReadCapped(big, SubmitFunction.MaxBodyBytes, TestContext.Current.CancellationToken));

        using var ok = new MemoryStream(Encoding.UTF8.GetBytes("name=Jeff"));
        Assert.Equal("name=Jeff", await SubmitFunction.ReadCapped(ok, SubmitFunction.MaxBodyBytes, TestContext.Current.CancellationToken));
    }

    [Fact]
    public void Every_topic_the_site_sends_has_its_own_acknowledgement_wording()
    {
        // The site's topics, as they appear in contact.html and tools/build_legal.py. A topic added to
        // the site and not here is acknowledged as "your message": not wrong, but worth noticing.
        string[] siteTopics =
        [
            "A walkthrough of the platform", "A scoped assessment (Copilot oversharing)",
            "A scoped assessment (email spoofing / DMARC)", "A security posture assessment",
            "A compliance readiness snapshot", "Partner / MSP model", "A quote for my estate",
            "Tell me when ConditionalAccessPortal ships", "Tell me when CompliancePortal ships",
            "Tell me when PosturePortal ships", "Tell me when Dredd ships", "Something else",
            "Pricing for my estate", "Free spoofing / DMARC check", "Free public surface scan",
            "Free exposure report",
        ];
        foreach (var t in siteTopics) Assert.True(Topics.IsKnown(t), t);
        Assert.Equal("your message", Topics.Phrase("anything else at all"));
    }
}
