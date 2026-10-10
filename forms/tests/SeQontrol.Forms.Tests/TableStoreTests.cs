using Azure.Data.Tables;
using SeQontrol.Forms;
using Xunit;

namespace SeQontrol.Forms.Tests;

/// <summary>
/// Runs against a real table endpoint when FORMS_TABLE_CONNECTION is set (for example Azurite:
/// "UseDevelopmentStorage=true"), and skips otherwise. CI runs it against Azurite.
/// </summary>
public class TableStoreTests
{
    private static TableSubmissionStore? Store()
    {
        var conn = Environment.GetEnvironmentVariable("FORMS_TABLE_CONNECTION");
        return string.IsNullOrEmpty(conn) ? null : new TableSubmissionStore(new TableServiceClient(conn));
    }

    [Fact]
    public async Task Submissions_are_stored_and_acknowledgements_throttled()
    {
        var store = Store();
        if (store is null) { Assert.Skip("FORMS_TABLE_CONNECTION not set"); return; }
        var ct = TestContext.Current.CancellationToken;

        var now = DateTimeOffset.UtcNow;
        var s = new Submission("Free exposure report", "Test", $"t{Guid.NewGuid():N}@example.com", "", "", "Hi",
            "/exposure-report.html", "", new Dictionary<string, string> { ["utm_source"] = "test" }, now);
        await store.SaveAsync(SubmissionHandler.NewId(now), s, ct);

        Assert.True(await store.TryClaimAcknowledgementAsync(s.Email, now, TimeSpan.FromHours(24), ct));
        Assert.False(await store.TryClaimAcknowledgementAsync(s.Email, now.AddMinutes(1), TimeSpan.FromHours(24), ct));
        Assert.True(await store.TryClaimAcknowledgementAsync(s.Email, now.AddHours(25), TimeSpan.FromHours(24), ct));

        var kind = $"test{Guid.NewGuid():N}";
        Assert.True(await store.TryConsumeMailBudgetAsync(kind, now, 2, ct));
        Assert.True(await store.TryConsumeMailBudgetAsync(kind, now, 2, ct));
        Assert.False(await store.TryConsumeMailBudgetAsync(kind, now, 2, ct));
        Assert.True(await store.TryConsumeMailBudgetAsync(kind, now.AddHours(1), 2, ct));
    }
}
