namespace SeQontrol.Forms;

/// <summary>A validated form submission, ready to store and to mail.</summary>
/// <remarks>
/// Every string here has already been length-capped and stripped of control characters by
/// <see cref="SubmissionValidator"/>. Nothing in it is trusted beyond that: it is what a stranger
/// typed into a public form.
/// </remarks>
public sealed record Submission(
    string Topic,
    string Name,
    string Email,
    string Organisation,
    string Estate,
    string Message,
    string Page,
    string Referrer,
    IReadOnlyDictionary<string, string> Utm,
    DateTimeOffset ReceivedUtc);

/// <summary>The outcome of validating a raw submission.</summary>
public abstract record ValidationOutcome
{
    private ValidationOutcome() { }

    /// <summary>The submission is complete and within limits.</summary>
    public sealed record Valid(Submission Submission) : ValidationOutcome;

    /// <summary>A person made a mistake; tell them what to fix.</summary>
    public sealed record Invalid(IReadOnlyList<string> Errors) : ValidationOutcome;

    /// <summary>
    /// A bot filled the trap field, or the form was submitted faster than a person can type.
    /// The caller answers exactly as it would for a real submission, so the bot learns nothing,
    /// and then stores and mails nothing.
    /// </summary>
    public sealed record Spam(string Reason) : ValidationOutcome;
}
