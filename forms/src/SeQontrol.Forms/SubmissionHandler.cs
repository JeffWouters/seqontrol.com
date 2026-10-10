using System.Text;
using Microsoft.Extensions.Logging;

namespace SeQontrol.Forms;

public sealed record FormsOptions
{
    /// <summary>Where new submissions are mailed. Replies go straight to the sender.</summary>
    public required string NotifyTo { get; init; }

    /// <summary>The address on the acknowledgement's Reply-To, so a reply reaches a person.</summary>
    public required string ReplyTo { get; init; }

    /// <summary>How long one inbox waits before it can receive another acknowledgement.</summary>
    public TimeSpan AcknowledgementWindow { get; init; } = TimeSpan.FromHours(24);

    /// <summary>Most notifications sent in any one hour. Far above real traffic; a flood stops here.</summary>
    public int NotificationsPerHour { get; init; } = 60;

    /// <summary>
    /// Most acknowledgements sent in any one hour. Lower than notifications on purpose: they go to
    /// addresses a stranger typed, so a flood of them is what gets a sending domain suspended.
    /// </summary>
    public int AcknowledgementsPerHour { get; init; } = 30;
}

public enum HandlerStatus { Accepted, Invalid }

public sealed record HandlerResult(HandlerStatus Status, IReadOnlyList<string> Errors)
{
    public static readonly HandlerResult Accepted = new(HandlerStatus.Accepted, []);
}

/// <summary>Validate, store, then mail. The order matters: nothing is mailed about what was not kept.</summary>
public sealed class SubmissionHandler(
    ISubmissionStore store,
    IMailer mailer,
    FormsOptions options,
    TimeProvider clock,
    ILogger<SubmissionHandler> log)
{
    public async Task<HandlerResult> HandleAsync(IReadOnlyDictionary<string, string> fields, CancellationToken ct)
    {
        var now = clock.GetUtcNow();
        switch (SubmissionValidator.Validate(fields, now))
        {
            case ValidationOutcome.Spam spam:
                // Answered exactly like a real submission, so the bot learns nothing from the reply.
                log.LogInformation("Submission discarded as spam ({Reason})", spam.Reason);
                return HandlerResult.Accepted;

            case ValidationOutcome.Invalid invalid:
                return new HandlerResult(HandlerStatus.Invalid, invalid.Errors);

            case ValidationOutcome.Valid valid:
                var s = valid.Submission;
                var id = NewId(now);

                // Throws on failure. The caller turns that into a 500, the page keeps the message in
                // the form and offers email instead, which is better than thanking someone for a
                // request nobody will ever see.
                await store.SaveAsync(id, s, ct);
                log.LogInformation("Submission {Id} stored (topic known: {Known})", id, Topics.IsKnown(s.Topic));

                if (await store.TryConsumeMailBudgetAsync("notification", now, options.NotificationsPerHour, ct))
                    await TrySend(Notification(id, s), "notification", id, ct);
                else
                    log.LogWarning("Notification for {Id} not sent: this hour's notification budget is spent. The submission is stored", id);

                if (!await store.TryClaimAcknowledgementAsync(s.Email, now, options.AcknowledgementWindow, ct))
                    log.LogInformation("Acknowledgement for {Id} skipped: one went to this address recently", id);
                else if (!await store.TryConsumeMailBudgetAsync("acknowledgement", now, options.AcknowledgementsPerHour, ct))
                    log.LogWarning("Acknowledgement for {Id} not sent: this hour's acknowledgement budget is spent", id);
                else
                    await TrySend(Acknowledgement(s), "acknowledgement", id, ct);

                return HandlerResult.Accepted;

            default:
                throw new InvalidOperationException("Unhandled validation outcome");
        }
    }

    private async Task TrySend(OutgoingMail mail, string kind, string id, CancellationToken ct)
    {
        if (!mailer.IsConfigured)
        {
            log.LogWarning("No mail sender configured; {Kind} for {Id} not sent. The submission is stored", kind, id);
            return;
        }
        try
        {
            await mailer.SendAsync(mail, ct);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // The submission is already stored, so a mail failure loses nothing: it is logged, and
            // the table still has the request. Failing the request here would ask a person to send
            // again something we already have.
            log.LogError(ex, "Sending the {Kind} for {Id} failed; the submission is stored", kind, id);
        }
    }

    /// <summary>Sortable newest-first within a partition, and unique.</summary>
    internal static string NewId(DateTimeOffset now) =>
        $"{DateTimeOffset.MaxValue.UtcTicks - now.UtcTicks:D19}-{Guid.NewGuid():N}";

    internal OutgoingMail Notification(string id, Submission s)
    {
        var body = new StringBuilder()
            .AppendLine($"Topic:        {Or(s.Topic)}")
            .AppendLine($"Name:         {s.Name}")
            .AppendLine($"Email:        {s.Email}")
            .AppendLine($"Organisation: {Or(s.Organisation)}")
            .AppendLine($"Estate:       {Or(s.Estate)}")
            .AppendLine($"Sent from:    {Or(s.Page)}")
            .AppendLine($"Referrer:     {Or(s.Referrer)}");
        foreach (var (k, v) in s.Utm)
            body.AppendLine($"{k + ":",-14}{v}");
        body.AppendLine($"Received:     {s.ReceivedUtc:yyyy-MM-dd HH:mm} UTC")
            .AppendLine($"Id:           {id}")
            .AppendLine()
            .AppendLine(s.Message.Length > 0 ? s.Message : "(no message)")
            .AppendLine()
            .AppendLine("Reply to this mail to answer them directly.");

        var subject = $"SeQontrol: {Or(s.Topic, "enquiry")} from {s.Name}";
        return new OutgoingMail(options.NotifyTo, Cap(subject, 200), body.ToString(), s.Email);
    }

    internal OutgoingMail Acknowledgement(Submission s)
    {
        // Nothing the sender typed appears in this mail; see Topics for why.
        var body =
            $"Thanks for getting in touch about {Topics.Phrase(s.Topic)}.\n\n" +
            "Your request reached us and is stored. A person reads every one and replies, usually the " +
            "same working day. If you want to add something, reply to this mail.\n\n" +
            "If you did not send a request to SeQontrol, you can ignore this mail: nothing further will " +
            "be sent to this address because of it.\n\n" +
            "SeQontrol, built by JeffOps\n" +
            "https://seqontrol.com/\n";
        return new OutgoingMail(s.Email, "We received your request", body, options.ReplyTo);
    }

    private static string Or(string value, string fallback = "-") => value.Length > 0 ? value : fallback;

    private static string Cap(string value, int max) => value.Length <= max ? value : value[..max];
}
