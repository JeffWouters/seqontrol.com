using SeQontrol.Forms;
using Xunit;

namespace SeQontrol.Forms.Tests;

public class ValidatorTests
{
    private static readonly DateTimeOffset Now = new(2026, 10, 10, 20, 0, 0, TimeSpan.Zero);

    private static Dictionary<string, string> Fields(params (string Key, string Value)[] extra)
    {
        var d = new Dictionary<string, string>
        {
            ["name"] = "Jeff",
            ["email"] = "jeff@example.com",
            ["topic"] = "Partner / MSP model",
            ["message"] = "Hello",
        };
        foreach (var (k, v) in extra) d[k] = v;
        return d;
    }

    [Fact]
    public void A_complete_submission_is_valid()
    {
        var outcome = Assert.IsType<ValidationOutcome.Valid>(SubmissionValidator.Validate(Fields(), Now));
        Assert.Equal("Jeff", outcome.Submission.Name);
        Assert.Equal(Now, outcome.Submission.ReceivedUtc);
    }

    [Fact]
    public void A_filled_honeypot_is_spam()
    {
        Assert.IsType<ValidationOutcome.Spam>(SubmissionValidator.Validate(Fields(("website", "http://x")), Now));
    }

    [Fact]
    public void A_form_sent_within_three_seconds_of_rendering_is_spam()
    {
        var ts = (Now - TimeSpan.FromSeconds(1)).ToUnixTimeMilliseconds().ToString();
        Assert.IsType<ValidationOutcome.Spam>(SubmissionValidator.Validate(Fields(("ts", ts)), Now));
    }

    [Fact]
    public void A_form_sent_after_a_human_pause_is_accepted()
    {
        var ts = (Now - TimeSpan.FromSeconds(40)).ToUnixTimeMilliseconds().ToString();
        Assert.IsType<ValidationOutcome.Valid>(SubmissionValidator.Validate(Fields(("ts", ts)), Now));
    }

    [Fact]
    public void A_missing_or_garbled_timestamp_is_not_held_against_the_sender()
    {
        Assert.IsType<ValidationOutcome.Valid>(SubmissionValidator.Validate(Fields(("ts", "nonsense")), Now));
        Assert.IsType<ValidationOutcome.Valid>(SubmissionValidator.Validate(Fields(("ts", long.MaxValue.ToString())), Now));
    }

    [Theory]
    [InlineData("", "jeff@example.com", "A name helps.")]
    [InlineData("Jeff", "", "We need an email address to reply to.")]
    [InlineData("Jeff", "not-an-address", "That email address does not look right.")]
    [InlineData("Jeff", "Jeff <jeff@example.com>", "That email address does not look right.")]
    [InlineData("Jeff", "jeff@localhost", "That email address does not look right.")]
    [InlineData("Jeff", "a@b.com,c@d.com", "That email address does not look right.")]
    public void Missing_or_wrong_contact_details_are_reported(string name, string email, string error)
    {
        var outcome = SubmissionValidator.Validate(Fields(("name", name), ("email", email)), Now);
        Assert.Contains(error, Assert.IsType<ValidationOutcome.Invalid>(outcome).Errors);
    }

    [Fact]
    public void Header_injection_characters_never_reach_single_line_fields()
    {
        var outcome = SubmissionValidator.Validate(
            Fields(("name", "Jeff\r\nBcc: victim@example.com"), ("topic", "x\nSubject: spam")), Now);
        var s = Assert.IsType<ValidationOutcome.Valid>(outcome).Submission;
        Assert.DoesNotContain('\n', s.Name);
        Assert.DoesNotContain('\r', s.Name);
        Assert.DoesNotContain('\n', s.Topic);
        Assert.Equal("Jeff Bcc: victim@example.com", s.Name);
    }

    [Fact]
    public void The_message_keeps_its_line_breaks_but_loses_other_control_characters()
    {
        var outcome = SubmissionValidator.Validate(Fields(("message", "line one\r\nline two\u0007")), Now);
        Assert.Equal("line one\nline two", Assert.IsType<ValidationOutcome.Valid>(outcome).Submission.Message);
    }

    [Fact]
    public void Long_fields_are_capped_not_rejected()
    {
        var outcome = SubmissionValidator.Validate(Fields(("message", new string('a', 20_000)), ("org", new string('b', 900))), Now);
        var s = Assert.IsType<ValidationOutcome.Valid>(outcome).Submission;
        Assert.Equal(SubmissionValidator.MessageMax, s.Message.Length);
        Assert.Equal(SubmissionValidator.OrganisationMax, s.Organisation.Length);
    }

    [Fact]
    public void A_cap_never_splits_a_surrogate_pair()
    {
        var name = new string('a', SubmissionValidator.NameMax - 1) + "😀";
        var s = Assert.IsType<ValidationOutcome.Valid>(SubmissionValidator.Validate(Fields(("name", name)), Now)).Submission;
        Assert.False(char.IsHighSurrogate(s.Name[^1]));
    }

    [Fact]
    public void Only_known_utm_fields_are_kept()
    {
        var outcome = SubmissionValidator.Validate(Fields(("utm_source", "linkedin"), ("utm_evil", "x"), ("utm_medium", "")), Now);
        var utm = Assert.IsType<ValidationOutcome.Valid>(outcome).Submission.Utm;
        Assert.Equal(new Dictionary<string, string> { ["utm_source"] = "linkedin" }, utm);
    }
}
