/**
 * Attachment limits. Mirror of backend/config/settings/base.py (ATTACHMENT_*):
 * change both together. The server is the authority; these only give faster feedback.
 */
export const ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024;
export const ATTACHMENT_MAX_PER_REQUEST = 5;
export const ATTACHMENT_ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'] as const;

export const COMMENT_MAX_LENGTH = 2000;

export function fileExtension(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase();
}

/** Client-side mirror of validators.validate_attachment. Returns an error message or null. */
export function validateAttachment(file: File, existingCount: number): string | null {
  const ext = fileExtension(file.name);
  if (existingCount >= ATTACHMENT_MAX_PER_REQUEST) {
    return `A request can have at most ${ATTACHMENT_MAX_PER_REQUEST} attachments.`;
  }
  if (!(ATTACHMENT_ALLOWED_EXTENSIONS as readonly string[]).includes(ext)) {
    return `'.${ext || '?'}' files are not allowed. Allowed: ${ATTACHMENT_ALLOWED_EXTENSIONS.join(', ')}.`;
  }
  if (file.size === 0) {
    return 'The file is empty.';
  }
  if (file.size > ATTACHMENT_MAX_BYTES) {
    return `The file is larger than ${ATTACHMENT_MAX_BYTES / (1024 * 1024)} MB.`;
  }
  return null;
}
