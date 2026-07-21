import test from 'node:test';
import assert from 'node:assert/strict';

import { canSubmitMessage } from './chatSubmission.js';

test('allows submission when input is non-empty and no lock is active', () => {
  assert.equal(
    canSubmitMessage({
      text: 'Привет',
      sending: false,
      isSubmitting: false,
      lastSubmittedAt: 0,
      now: 1000,
      cooldownMs: 500,
    }),
    true,
  );
});

test('blocks submission while a request is already in progress', () => {
  assert.equal(
    canSubmitMessage({
      text: 'Привет',
      sending: true,
      isSubmitting: false,
      lastSubmittedAt: 0,
      now: 1000,
      cooldownMs: 500,
    }),
    false,
  );
});

test('blocks immediate repeated submissions within cooldown window', () => {
  assert.equal(
    canSubmitMessage({
      text: 'Привет',
      sending: false,
      isSubmitting: false,
      lastSubmittedAt: 900,
      now: 1000,
      cooldownMs: 500,
    }),
    false,
  );
});
