export function canSubmitMessage({
  text,
  sending,
  isSubmitting,
  lastSubmittedAt,
  now,
  cooldownMs = 400,
}) {
  const trimmed = text?.trim?.() || '';
  if (!trimmed) return false;
  if (sending || isSubmitting) return false;
  if (
    lastSubmittedAt &&
    now - lastSubmittedAt < cooldownMs
  ) {
    return false;
  }
  return true;
}
