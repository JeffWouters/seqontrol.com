using Azure.Communication.Email;
using Azure.Core;
using Azure.Data.Tables;
using Azure.Identity;
using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using SeQontrol.Forms;

// Settings, all plain app settings (infra/forms/main.bicep sets them):
//   AZURE_CLIENT_ID               the user-assigned identity the app runs as (absent locally: az login)
//   SUBMISSIONS_TABLE_ENDPOINT    https://<account>.table.core.windows.net
//   SUBMISSIONS_STORAGE_CONNECTION  local only, e.g. UseDevelopmentStorage=true for Azurite
//   ACS_ENDPOINT, MAIL_FROM       Azure Communication Services Email; both empty = mail skipped, logged
//   NOTIFY_TO, REPLY_TO           who is told about a submission; where replies to the acknowledgement go
//   ALLOWED_ORIGINS               comma-separated, e.g. https://seqontrol.com,https://www.seqontrol.com
//   THANKS_URL                    where a browser without JavaScript lands after posting

static string Setting(string name, string? fallback = null) =>
    Environment.GetEnvironmentVariable(name) is { Length: > 0 } v ? v
    : fallback ?? throw new InvalidOperationException($"App setting {name} is required.");

var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults()
    .ConfigureServices(services =>
    {
        services.AddApplicationInsightsTelemetryWorkerService();
        services.ConfigureFunctionsApplicationInsights();

        var credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
        {
            ManagedIdentityClientId = Environment.GetEnvironmentVariable("AZURE_CLIENT_ID"),
        });
        services.AddSingleton<TokenCredential>(credential);

        // The Application Insights resource accepts Entra-authenticated telemetry only (local auth is
        // off in main.bicep). APPLICATIONINSIGHTS_AUTHENTICATION_STRING covers the Functions host, not
        // this worker's own SDK, so without this the worker's logs - including "a mail failed" - would
        // be rejected and nobody would see them. Skipped locally, where no connection string is set.
        if (Environment.GetEnvironmentVariable("AZURE_CLIENT_ID") is { Length: > 0 })
            services.Configure<TelemetryConfiguration>(c => c.SetAzureTokenCredential(credential));

        services.AddSingleton(sp =>
            Environment.GetEnvironmentVariable("SUBMISSIONS_STORAGE_CONNECTION") is { Length: > 0 } local
                ? new TableServiceClient(local)
                : new TableServiceClient(new Uri(Setting("SUBMISSIONS_TABLE_ENDPOINT")), sp.GetRequiredService<TokenCredential>()));
        services.AddSingleton<ISubmissionStore, TableSubmissionStore>();

        services.AddSingleton<IMailer>(sp =>
        {
            var endpoint = Environment.GetEnvironmentVariable("ACS_ENDPOINT");
            var from = Environment.GetEnvironmentVariable("MAIL_FROM");
            return endpoint is { Length: > 0 } && from is { Length: > 0 }
                ? new AcsMailer(new EmailClient(new Uri(endpoint), sp.GetRequiredService<TokenCredential>()), from)
                : new UnconfiguredMailer();
        });

        services.AddSingleton(new FormsOptions
        {
            NotifyTo = Setting("NOTIFY_TO"),
            ReplyTo = Setting("REPLY_TO", Environment.GetEnvironmentVariable("NOTIFY_TO")),
        });
        services.AddSingleton(new EndpointOptions
        {
            AllowedOrigins = Setting("ALLOWED_ORIGINS")
                .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Select(o => o.TrimEnd('/'))
                .ToHashSet(StringComparer.OrdinalIgnoreCase),
            ThanksUrl = new Uri(Setting("THANKS_URL", "https://seqontrol.com/thanks.html")),
        });
        services.AddSingleton(TimeProvider.System);
        services.AddSingleton<SubmissionHandler>();
    })
    .Build();

host.Run();
