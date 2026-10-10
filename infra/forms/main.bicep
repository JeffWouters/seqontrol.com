// The form backend for seqontrol.com: one HTTP function that stores each submission in Table
// Storage, mails it to us, and acknowledges it to the sender through Azure Communication Services.
//
// Deploy into an empty resource group in an EU region (README, "Form backend"):
//
//   az group create -n rg-seqontrol-forms -l westeurope
//   az deployment group create -g rg-seqontrol-forms -f infra/forms/main.bicep
//
// Mail is a second step, because ACS will not link a domain whose DNS records are not in place yet.
// The first deployment creates the mail domain and prints the records to add; once they verify,
// deploy again with linkMailDomain=true. Until then submissions are stored but nothing is mailed,
// and the function logs a warning for each one.
//
// Nothing here uses a key or a connection string: the app runs as a user-assigned identity with
// data-plane roles on exactly the resources it touches, and the storage account refuses shared keys.

targetScope = 'resourceGroup'

@description('Region for everything except ACS, which is global with its data held in Europe. Flex Consumption is not in every region: check `az functionapp list-flexconsumption-locations`.')
param location string = resourceGroup().location

@description('Base name for the resources.')
@minLength(3)
@maxLength(20)
param name string = 'seqontrol-forms'

@description('Origins allowed to post the forms. Compared exactly, so list www separately if it serves pages.')
param allowedOrigins array = [
  'https://seqontrol.com'
  'https://www.seqontrol.com'
]

@description('Where new submissions are mailed.')
param notifyTo string = 'jeff@jeffops.com'

@description('Reply-To on the acknowledgement, so a reply reaches a person.')
param replyTo string = notifyTo

@description('Where a browser without JavaScript lands after a successful post.')
param thanksUrl string = 'https://seqontrol.com/thanks.html'

@description('The domain acknowledgements are sent from. A subdomain keeps ACS out of the apex domain\'s own SPF and DMARC setup.')
param mailDomain string = 'mail.seqontrol.com'

@description('Local part of the sending address, so mail comes from <mailSender>@<mailDomain>.')
param mailSender string = 'noreply'

@description('Set to true only after the mail domain\'s DNS records have verified. Links the domain to ACS and turns mail on.')
param linkMailDomain bool = false

@description('Memory per instance. A form handler needs little; 512 MB is the smallest Flex Consumption size.')
@allowed([512, 2048, 4096])
param instanceMemoryMB int = 512

@description('Upper bound on scale-out. Also a ceiling on what a flood of requests can cost.')
@minValue(40)
@maxValue(1000)
param maximumInstanceCount int = 40

var token = uniqueString(resourceGroup().id)
var storageName = take('stforms${token}', 24)
var deploymentContainer = 'deployments'

// Built-in role definition IDs.
var roles = {
  storageBlobDataOwner: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  storageTableDataContributor: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
  monitoringMetricsPublisher: '3913510d-42f4-4e42-8a64-420c390055eb'
}

// ---------------------------------------------------------------- monitoring

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${name}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${name}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
    DisableLocalAuth: true
  }
}

// ---------------------------------------------------------------- identity

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${name}'
  location: location
}

// ---------------------------------------------------------------- storage

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource deployments 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: deploymentContainer
  properties: { publicAccess: 'None' }
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource submissionsTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = {
  parent: tableService
  name: 'submissions'
}

resource acknowledgementsTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = {
  parent: tableService
  name: 'acknowledgements'
}

resource blobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, roles.storageBlobDataOwner)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataOwner)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource queueContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, roles.storageQueueDataContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageQueueDataContributor)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource tableContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, roles.storageTableDataContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageTableDataContributor)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource metricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, identity.id, roles.monitoringMetricsPublisher)
  scope: insights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.monitoringMetricsPublisher)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------- mail

resource emailService 'Microsoft.Communication/emailServices@2023-04-01' = {
  name: 'acs-email-${name}'
  location: 'global'
  properties: {
    dataLocation: 'Europe'
  }
}

resource domain 'Microsoft.Communication/emailServices/domains@2023-04-01' = {
  parent: emailService
  name: mailDomain
  location: 'global'
  properties: {
    domainManagement: 'CustomerManaged'
    userEngagementTracking: 'Disabled'
  }
}

resource sender 'Microsoft.Communication/emailServices/domains/senderUsernames@2023-04-01' = {
  parent: domain
  name: mailSender
  properties: {
    username: mailSender
    displayName: 'SeQontrol'
  }
}

resource communication 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: 'acs-${name}'
  location: 'global'
  properties: {
    dataLocation: 'Europe'
    linkedDomains: linkMailDomain ? [domain.id] : []
  }
}

// Sending with an Entra identity needs these three actions and nothing else (Microsoft documents this
// exact set). Contributor would also let the identity read and regenerate the ACS access keys, and a
// key is a credential that works without the identity, which is what this template avoids everywhere.
resource emailSenderRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'seqontrol-forms-email-sender')
  properties: {
    roleName: 'SeQontrol forms email sender (${resourceGroup().name})'
    description: 'Send email through Azure Communication Services, nothing more.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'Microsoft.Communication/CommunicationServices/Read'
          'Microsoft.Communication/CommunicationServices/Write'
          'Microsoft.Communication/EmailServices/write'
        ]
        notActions: []
      }
    ]
    assignableScopes: [resourceGroup().id]
  }
}

resource acsSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(communication.id, identity.id, emailSenderRole.id)
  scope: communication
  properties: {
    roleDefinitionId: emailSenderRole.id
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------- function app

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: 'plan-${name}'
  location: location
  kind: 'functionapp'
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  properties: {
    reserved: true
  }
}

resource app 'Microsoft.Web/sites@2024-04-01' = {
  name: '${name}-${token}'
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      cors: {
        allowedOrigins: allowedOrigins
        supportCredentials: false
      }
      appSettings: [
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
        { name: 'AzureWebJobsStorage__clientId', value: identity.properties.clientId }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
        { name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING', value: 'ClientId=${identity.properties.clientId};Authorization=AAD' }
        { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
        { name: 'SUBMISSIONS_TABLE_ENDPOINT', value: storage.properties.primaryEndpoints.table }
        { name: 'NOTIFY_TO', value: notifyTo }
        { name: 'REPLY_TO', value: replyTo }
        { name: 'ALLOWED_ORIGINS', value: join(allowedOrigins, ',') }
        { name: 'THANKS_URL', value: thanksUrl }
        { name: 'ACS_ENDPOINT', value: linkMailDomain ? 'https://${communication.properties.hostName}' : '' }
        { name: 'MAIL_FROM', value: linkMailDomain ? '${mailSender}@${mailDomain}' : '' }
      ]
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentContainer}'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: identity.id
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: maximumInstanceCount
        instanceMemoryMB: instanceMemoryMB
      }
      runtime: {
        name: 'dotnet-isolated'
        version: '10.0'
      }
    }
  }
  dependsOn: [
    blobOwner
    queueContributor
    tableContributor
    metricsPublisher
    deployments
    submissionsTable
    acknowledgementsTable
  ]
}

// ---------------------------------------------------------------- outputs

@description('Paste this into FORM_ENDPOINT in tools/build_legal.py.')
output formEndpoint string = 'https://${app.properties.defaultHostName}/api/submit'

output functionAppName string = app.name

@description('Add these to the DNS of the mail domain, then verify the domain in ACS before redeploying with linkMailDomain=true.')
output mailDomainVerificationRecords object = domain.properties.verificationRecords

output mailFrom string = '${mailSender}@${mailDomain}'
