import test from 'node:test';
import assert from 'node:assert/strict';

import { normalizeWebSocketMessage } from './websocketService.js';

test('normalizes message_update events from nested data field', () => {
  const event = {
    type: 'message_update',
    question_id: 'q-1',
    data: {
      uuid: 'm-1',
      question_id: 'q-1',
      text: 'Привет',
      sender_type: 'user',
    },
  };

  const normalized = normalizeWebSocketMessage(event);

  assert.equal(normalized.type, 'message_update');
  assert.equal(normalized.questionId, 'q-1');
  assert.deepEqual(normalized.payload, event.data);
});

test('normalizes payload-style events when data wrapper is absent', () => {
  const event = {
    type: 'message_update',
    question_id: 'q-2',
    payload: {
      uuid: 'm-2',
      question_id: 'q-2',
      text: 'Ответ',
      sender_type: 'pharmacist',
    },
  };

  const normalized = normalizeWebSocketMessage(event);

  assert.equal(normalized.type, 'message_update');
  assert.equal(normalized.questionId, 'q-2');
  assert.deepEqual(normalized.payload, event.payload);
});
