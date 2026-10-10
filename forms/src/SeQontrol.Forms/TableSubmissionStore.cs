using System.Security.Cryptography;
using System.Text;
using Azure;
using Azure.Data.Tables;

namespace SeQontrol.Forms;

/// <summary>Submissions in Azure Table Storage: one table for requests, one for acknowledgement throttling.</summary>
public sealed class TableSubmissionStore(TableServiceClient service) : ISubmissionStore
{
    public const string SubmissionsTable = "submissions";
    public const string AcknowledgementsTable = "acknowledgements";

    private readonly TableClient _submissions = service.GetTableClient(SubmissionsTable);
    private readonly TableClient _acks = service.GetTableClient(AcknowledgementsTable);
    private readonly SemaphoreSlim _ensure = new(1, 1);
    private volatile bool _ensured;

    // The Bicep template creates both tables, so in Azure this is two no-op calls on the first request
    // of an instance. It exists for local runs against Azurite, where nothing created them.
    private async Task EnsureTablesAsync(CancellationToken ct)
    {
        if (_ensured) return;
        await _ensure.WaitAsync(ct);
        try
        {
            if (_ensured) return;
            await _submissions.CreateIfNotExistsAsync(ct);
            await _acks.CreateIfNotExistsAsync(ct);
            _ensured = true;
        }
        finally { _ensure.Release(); }
    }

    public async Task SaveAsync(string id, Submission s, CancellationToken ct)
    {
        await EnsureTablesAsync(ct);
        // Partitioned by month: the natural unit for "what came in", and it keeps any one partition small.
        var entity = new TableEntity(s.ReceivedUtc.ToString("yyyy-MM"), id)
        {
            ["Topic"] = s.Topic,
            ["Name"] = s.Name,
            ["Email"] = s.Email,
            ["Organisation"] = s.Organisation,
            ["Estate"] = s.Estate,
            ["Message"] = s.Message,
            ["Page"] = s.Page,
            ["Referrer"] = s.Referrer,
            ["ReceivedUtc"] = s.ReceivedUtc,
        };
        foreach (var (k, v) in s.Utm)
            entity[k] = v;

        await _submissions.AddEntityAsync(entity, ct);
    }

    public async Task<bool> TryClaimAcknowledgementAsync(string email, DateTimeOffset now, TimeSpan window, CancellationToken ct)
    {
        // The address itself is not kept here, only a hash of it: this table exists to count, and
        // the address is already in the submission it belongs to.
        await EnsureTablesAsync(ct);
        var key = Hash(email);
        var existing = await _acks.GetEntityIfExistsAsync<TableEntity>("ack", key, cancellationToken: ct);
        if (existing.HasValue && existing.Value!.GetDateTimeOffset("SentUtc") is { } last && now - last < window)
            return false;

        var claim = new TableEntity("ack", key) { ["SentUtc"] = now };
        try
        {
            if (existing.HasValue)
                await _acks.UpdateEntityAsync(claim, existing.Value!.ETag, TableUpdateMode.Replace, ct);
            else
                await _acks.AddEntityAsync(claim, ct);
            return true;
        }
        catch (RequestFailedException ex) when (ex.Status is 409 or 412)
        {
            // Two submissions from one address raced; the other one sends the acknowledgement.
            return false;
        }
    }

    public async Task<bool> TryConsumeMailBudgetAsync(string kind, DateTimeOffset now, int limit, CancellationToken ct)
    {
        await EnsureTablesAsync(ct);
        var row = $"{kind}-{now.UtcDateTime:yyyyMMddHH}";

        // Optimistic concurrency on one counter row per kind per hour. A handful of retries is plenty
        // at real volumes; under a flood, losing a race simply means that request sends nothing.
        for (var attempt = 0; attempt < 5; attempt++)
        {
            var current = await _acks.GetEntityIfExistsAsync<TableEntity>("budget", row, cancellationToken: ct);
            var used = current.HasValue ? current.Value!.GetInt32("Used") ?? 0 : 0;
            if (used >= limit) return false;

            var next = new TableEntity("budget", row) { ["Used"] = used + 1 };
            try
            {
                if (current.HasValue)
                    await _acks.UpdateEntityAsync(next, current.Value!.ETag, TableUpdateMode.Replace, ct);
                else
                    await _acks.AddEntityAsync(next, ct);
                return true;
            }
            catch (RequestFailedException ex) when (ex.Status is 409 or 412)
            {
                // Somebody else took a unit first; read again.
            }
        }
        return false;
    }

    /// <summary>
    /// The throttle key for an address. Plus-tags are dropped, and dots in a Gmail local part, so
    /// victim+1@gmail.com and v.ictim@gmail.com count as the inbox they all deliver to.
    /// </summary>
    internal static string Hash(string email) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Normalise(email))));

    internal static string Normalise(string email)
    {
        var address = email.Trim().ToLowerInvariant();
        var at = address.LastIndexOf('@');
        if (at <= 0) return address;
        var local = address[..at];
        var domain = address[(at + 1)..];
        var plus = local.IndexOf('+');
        if (plus > 0) local = local[..plus];
        if (domain is "gmail.com" or "googlemail.com")
        {
            local = local.Replace(".", "");
            domain = "gmail.com";
        }
        return $"{local}@{domain}";
    }
}
