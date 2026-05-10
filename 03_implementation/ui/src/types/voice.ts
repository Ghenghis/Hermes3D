export interface AgentVoice {
  agentId: string;
  agentName: string;
  voiceName: string;
  provider: "azure" | "local";
}

export interface VoiceProvider {
  id: string;
  name: string;
  configured: boolean;
  status?: "ready" | "not_configured" | "not_installed" | "unreachable" | "azure_error";
  region?: string | null;
  source?: string | null;
}

export interface VoiceAgent {
  id: string;
  name: string;
  voice: string;
  provider: VoiceProvider["id"];
}

export interface AzureVoice {
  id: string;
  shortName: string;
  displayName: string;
  localName: string;
  locale: string;
  gender: string;
  styles: string[];
}

export interface VoiceCatalog {
  provider: "azure";
  configured: boolean;
  status: "ready" | "not_configured" | "unreachable" | "azure_error";
  region?: string | null;
  reason?: string;
  count: number;
  voices: AzureVoice[];
}

export interface VoicePreviewResult {
  accepted: boolean;
  status: "ready" | "not_configured" | "not_installed" | "unreachable" | "azure_error" | "invalid_response";
  reason?: string;
  voice?: string;
  mimeType?: string;
  audioBase64?: string;
  bytes?: number;
  proofEventId?: string;
}

export interface VoiceTranscript {
  id: string;
  eventType: string;
  status: string;
  locale: string;
  transcript: string;
  transcriptSha256?: string;
  phraseCount?: number;
  bytes?: number;
  provider: string;
  tsUtc: string;
  proofEventId: string;
}

export interface VoiceProofEvent {
  id: string;
  eventType: string;
  sourceAgent: string;
  status: string;
  tsUtc: string;
  summary: string;
}
