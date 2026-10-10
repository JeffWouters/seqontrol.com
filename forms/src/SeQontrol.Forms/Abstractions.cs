namespace SeQontrol.Forms;

/// <summary>Where submissions are kept. The table is the record; mail is only a notification of it.</summary>
public interface ISubmissionStore
{
    /// <summary>Stores a submission. Throws if it could not be stored, so the sender is told it failed.</summary>
    Task SaveAsync(string id, Submission submission, CancellationToken ct);

    /// <summary>
    /// Records that an acknowledgement is about to go to this address. Returns false when one already
    /// went in the last <paramref name="window"/>, so a form cannot be used to mail one inbox repeatedly.
    /// </summary>
    Task<bool> TryClaimAcknowledgementAsync(string email, DateTimeOffset now, TimeSpan window, CancellationToken ct);

    /// <summary>
    /// Takes one unit from this hour's budget for <paramref name="kind"/>. Returns false once
    /// <paramref name="limit"/> is spent. A script that gets past the spam checks can still fill the
    /// table, but it cannot turn the form into a mail cannon: once the hour's mail is spent,
    /// submissions are stored and nothing more is sent until the next hour.
    /// </summary>
    Task<bool> TryConsumeMailBudgetAsync(string kind, DateTimeOffset now, int limit, CancellationToken ct);
}

/// <summary>A plain-text mail.</summary>
public sealed record OutgoingMail(string To, string Subject, string Body, string? ReplyTo);

public interface IMailer
{
    /// <summary>True when a sender is configured; false means mail is skipped and only logged.</summary>
    bool IsConfigured { get; }

    Task SendAsync(OutgoingMail mail, CancellationToken ct);
}
