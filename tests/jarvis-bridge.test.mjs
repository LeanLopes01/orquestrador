import {test} from 'node:test';
import assert from 'node:assert/strict';
import {allowedRoute,localRequest} from '../services/jarvis-bridge.mjs';
test('local bridge rejects other origins, hosts and unapproved mutations',()=>{
  assert.equal(localRequest({headers:{host:'127.0.0.1:1420',origin:'http://evil.example'}}),false);
  assert.equal(localRequest({headers:{host:'evil.example:1420'}}),false);
  assert.equal(localRequest({headers:{host:'localhost:1420','sec-fetch-site':'cross-site'}}),false);
  assert.equal(localRequest({headers:{host:'127.0.0.1:1420',origin:'http://127.0.0.1:1420'}}),true);
  assert.equal(allowedRoute('POST','/v1/conversations'),true);
  assert.equal(allowedRoute('GET','/v1/conversations/abc-123'),true);
  for(const path of ['/v1/runs/abc/apply','/v1/devices','//evil.example','/v1/conversations/../devices','/v1/conversations?url=https://evil.example'])assert.equal(allowedRoute('POST',path),false);
});
