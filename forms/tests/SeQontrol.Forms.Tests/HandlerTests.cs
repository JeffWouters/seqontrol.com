using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Time.Testing;
using SeQontrol.Forms;
using Xunit;

namespace SeQontrol.Forms.Tests;

public class HandlerTests
{
    private sealed class FakeStore : ISubmissionStore
    {
        public List<(string Id, Submission S)> Saved { get; } = [];
        public Dictionary<string, DateTimeOffset> Acks { get; } = [];
        public bool FailSave { get; set; }

        public Task SaveAsync(string id, Submission submission, CancellationToken ct)
        {
            if (FailSave) throw new InvalidOperationException("storage down");
            Saved.Add((id, submission));
            return Task.CompletedTask;
        }

        public Dictionary<string, int> Budget { get; } = [];

        public Task<bool> TryConsumeMailBudgetAsync(string kind, DateTimeOffset now, int limit, CancellationToken ct)
        {
            var key = $"{kind}-{now.UtcDateTime:yyyyMMddHH}";
            Budget.TryGetValue(key, out var used);
            if (used >= limit) return Task.FromResult(false);
            Budget[key] = used + 1;
            return Task.FromResult(true);
        }

        public Task<bool> TryClaimAcknowledgementAsync(string email, DateTimeOffset now, TimeSpan window, CancellationToken ct)
        {
            var key = TableSubmissionStore.Hash(email);
            if (Acks.TryGetValue(key, out var last) && now - last < window) return Task.FromResult(false);
            Acks[key] = now;
            return Task.FromResult(true);
        }
    }

    private sealed class FakeMailer(bool configured = true, bool fail = false) : IMailer
    {
        public List<OutgoingMail> Sent { get; } = [];
        public bool IsConfigured => configured;

        public Task SendAsync(OutgoingMail mail, CancellationToken ct)
        {
            if (fail) throw new InvalidOperationException("mail down");
            Sent.Add(mail);
            return Task.CompletedTask;
        }
    }

    private static readonly FormsOptions Options = new() { NotifyTo = "jeff@jeffops.com", ReplyTo = "jeff@jeffops.com" };

    private static Dictionary<string, string> Form(string email = "visitor@example.com", string message = "Hi") => new()
    {
        ["name"] = "Visitor",
        ["email"] = email,
        ["topic"] = "Free exposure report",
        ["message"] = message,
        ["page"] = "/exposure-report.html",
        ["utm_source"] = "linkedin",
    };

    private static (SubmissionHandler, FakeStore, FakeMailer, FakeTimeProvider) Make(FakeMailer? mailer = null)
    {
        var store = new FakeStore();
        mailer ??= new FakeMailer();
        var clock = new FakeTimeProvider(new DateTimeOffset(2026, 10, 10, 20, 0, 0, TimeSpan.Zero));
        return (new SubmissionHandler(store, mailer, Options, clock, NullLogger<SubmissionHandler>.Instance), store, mailer, clock);
    }

    [Fact]
    public async Task A_valid_submission_is_stored_then_notified_and_acknowledged()
    {
        var (handler, store, mailer, _) = Make();
        var result = await handler.HandleAsync(Form(), TestContext.Current.CancellationToken);

        Assert.Equal(HandlerStatus.Accepted, result.Status);
        Assert.Single(store.Saved);
        Assert.Equal(2, mailer.Sent.Count);

        var notify = mailer.Sent[0];
        Assert.Equal("jeff@jeffops.com", notify.To);
        Assert.Equal("visitor@example.com", notify.ReplyTo);
        Assert.Contains("utm_source:", notify.Body);
        Assert.Contains("/exposure-report.html", notify.Body);

        var ack = mailer.Sent[1];
        Assert.Equal("visitor@example.com", ack.To);
        Assert.Equal("jeff@jeffops.com", ack.ReplyTo);
        Assert.Contains("a free exposure report", ack.Body);
    }

    [Fact]
    public async Task The_acknowledgement_never_carries_what_the_sender_typed()
    {
        var (handler, _, mailer, _) = Make();
        var form = Form(message: "Buy cheap pills at spam.example");
        form["name"] = "Click spam.example now";
        form["topic"] = "Visit spam.example";
        await handler.HandleAsync(form, TestContext.Current.CancellationToken);

        var ack = mailer.Sent.Single(m => m.To == "visitor@example.com");
        Assert.DoesNotContain("spam.example", ack.Body);
        Assert.DoesNotContain("spam.example", ack.Subject);
        Assert.Contains("your message", ack.Body);
    }

    [Fact]
    public async Task One_inbox_gets_one_acknowledgement_a_day()
    {
        var (handler, store, mailer, clock) = Make();
        await handler.HandleAsync(Form(), TestContext.Current.CancellationToken);
        clock.Advance(TimeSpan.FromMinutes(5));
        await handler.HandleAsync(Form(email: "VISITOR@example.com"), TestContext.Current.CancellationToken);

        Assert.Equal(2, store.Saved.Count);
        Assert.Equal(1, mailer.Sent.Count(m => m.To.Equals("visitor@example.com", StringComparison.OrdinalIgnoreCase)));
        Assert.Equal(2, mailer.Sent.Count(m => m.To == "jeff@jeffops.com"));

        clock.Advance(TimeSpan.FromHours(25));
        await handler.HandleAsync(Form(), TestContext.Current.CancellationToken);
        Assert.Equal(2, mailer.Sent.Count(m => m.To.Equals("visitor@example.com", StringComparison.OrdinalIgnoreCase)));
    }

    [Fact]
    public async Task Spam_is_answered_as_accepted_but_nothing_is_stored_or_sent()
    {
        var (handler, store, mailer, _) = Make();
        var form = Form();
        form["website"] = "http://bot.example";
        var result = await handler.HandleAsync(form, TestContext.Current.CancellationToken);

        Assert.Equal(HandlerStatus.Accepted, result.Status);
        Assert.Empty(store.Saved);
        Assert.Empty(mailer.Sent);
    }

    [Fact]
    public async Task A_mail_failure_does_not_fail_a_stored_submission()
    {
        var (handler, store, _, _) = Make(new FakeMailer(fail: true));
        var result = await handler.HandleAsync(Form(), TestContext.Current.CancellationToken);
        Assert.Equal(HandlerStatus.Accepted, result.Status);
        Assert.Single(store.Saved);
    }

    [Fact]
    public async Task Without_a_mail_sender_submissions_are_still_stored()
    {
        var (handler, store, mailer, _) = Make(new FakeMailer(configured: false));
        await handler.HandleAsync(Form(), TestContext.Current.CancellationToken);
        Assert.Single(store.Saved);
        Assert.Empty(mailer.Sent);
    }

    [Fact]
    public async Task A_storage_failure_propagates_so_the_sender_is_told()
    {
        var (handler, store, mailer, _) = Make();
        store.FailSave = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() => handler.HandleAsync(Form(), TestContext.Current.CancellationToken));
        Assert.Empty(mailer.Sent);
    }

    [Fact]
    public async Task Invalid_input_is_reported_and_nothing_is_stored()
    {
        var (handler, store, mailer, _) = Make();
        var result = await handler.HandleAsync(Form(email: "nope"), TestContext.Current.CancellationToken);
        Assert.Equal(HandlerStatus.Invalid, result.Status);
        Assert.Empty(store.Saved);
        Assert.Empty(mailer.Sent);
    }

    [Fact]
    public async Task A_flood_is_stored_but_mail_stops_at_the_hourly_budget()
    {
        var store = new FakeStore();
        var mailer = new FakeMailer();
        var clock = new FakeTimeProvider(new DateTimeOffset(2026, 10, 10, 20, 0, 0, TimeSpan.Zero));
        var options = Options with { NotificationsPerHour = 5, AcknowledgementsPerHour = 3 };
        var handler = new SubmissionHandler(store, mailer, options, clock, NullLogger<SubmissionHandler>.Instance);

        for (var i = 0; i < 20; i++)
            await handler.HandleAsync(Form(email: $"victim{i}@example.com"), TestContext.Current.CancellationToken);

        Assert.Equal(20, store.Saved.Count);
        Assert.Equal(5, mailer.Sent.Count(m => m.To == "jeff@jeffops.com"));
        Assert.Equal(3, mailer.Sent.Count(m => m.To != "jeff@jeffops.com"));

        clock.Advance(TimeSpan.FromHours(1));
        await handler.HandleAsync(Form(email: "next-hour@example.com"), TestContext.Current.CancellationToken);
        Assert.Equal(6, mailer.Sent.Count(m => m.To == "jeff@jeffops.com"));
    }

    [Theory]
    [InlineData("Victim+1@Gmail.com", "victim@gmail.com")]
    [InlineData("v.i.c.t.i.m@googlemail.com", "victim@gmail.com")]
    [InlineData("first.last+news@example.com", "first.last@example.com")]
    public void Address_variants_share_one_throttle_key(string variant, string canonical)
    {
        Assert.Equal(TableSubmissionStore.Hash(canonical), TableSubmissionStore.Hash(variant));
    }

    [Fact]
    public void Ids_sort_newest_first()
    {
        var older = SubmissionHandler.NewId(new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero));
        var newer = SubmissionHandler.NewId(new DateTimeOffset(2026, 1, 2, 0, 0, 0, TimeSpan.Zero));
        Assert.True(string.CompareOrdinal(newer, older) < 0);
    }
}
