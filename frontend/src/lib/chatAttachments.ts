/**
 * MIME types accepted by the chat file picker — aligns with
 * `smart_report_analyst.service.strands.user_turn` / Bedrock document formats.
 */
export const CHAT_ATTACHMENTS_ACCEPT = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/html",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
].join(",");

/** Default matches CopilotKit Chat.tsx (20 MiB). */
export const CHAT_ATTACHMENTS_MAX_BYTES = 20 * 1024 * 1024;
