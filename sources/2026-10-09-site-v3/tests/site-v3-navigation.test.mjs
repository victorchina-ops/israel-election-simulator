import test from 'node:test';import assert from 'node:assert/strict';
import {shouldOpenAbout} from '../dashboard/src/content/dashboard/site-navigation.js';
test('fresh visits land on About, including version-only links',()=>{
 assert.equal(shouldOpenAbout('https://example.test/'),true);
 assert.equal(shouldOpenAbout('https://example.test/?version=v3'),true);
});
test('explicit tab and source component links retain their destinations',()=>{
 assert.equal(shouldOpenAbout('https://example.test/?tab=dashboard'),false);
 assert.equal(shouldOpenAbout('https://example.test/?tab=poll-trends&view=1'),false);
 assert.equal(shouldOpenAbout('https://example.test/_data/charts/abc12345'),false);
 assert.equal(shouldOpenAbout('https://example.test/_data/components/abc12345'),false);
 assert.equal(shouldOpenAbout(null),false);
});
