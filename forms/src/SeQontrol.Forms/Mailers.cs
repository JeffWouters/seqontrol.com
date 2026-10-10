using Azure;
using Azure.Communication.Email;

namespace SeQontrol.Forms;

/// <summary>Sends through Azure Communication Services Email, from an address on a verified domain.</summary>
public sealed class AcsMailer(EmailClient client, string fromAddress) : IMailer
{
    public bool IsConfigured => true;

    public async Task SendAsync(OutgoingMail mail, CancellationToken ct)
    {
        var message = new EmailMessage(
            senderAddress: fromAddress,
            recipients: new EmailRecipients([new EmailAddress(mail.To)]),
            content: new EmailContent(mail.Subject) { PlainText = mail.Body });
        if (mail.ReplyTo is { Length: > 0 } replyTo)
            message.ReplyTo.Add(new EmailAddress(replyTo));

        // WaitUntil.Started: the service has accepted the mail. Waiting for delivery would hold the
        // visitor's request open for as long as the receiving server takes, for nothing they can act on.
        await client.SendAsync(WaitUntil.Started, message, ct);
    }
}

/// <summary>Used until ACS is set up: submissions are still stored, and the handler logs what it skipped.</summary>
public sealed class UnconfiguredMailer : IMailer
{
    public bool IsConfigured => false;

    public Task SendAsync(OutgoingMail mail, CancellationToken ct) => Task.CompletedTask;
}
