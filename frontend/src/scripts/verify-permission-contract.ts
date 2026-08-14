import assert from 'node:assert/strict';

import {
  canAdministerSystem,
  canManageInventory,
  canReadInventory,
  type AppRole,
} from '../lib/permissions';

const roles: AppRole[] = ['super_admin', 'item_manager', 'read_only_user'];

assert.equal(canReadInventory('super_admin'), true);
assert.equal(canReadInventory('item_manager'), true);
assert.equal(canReadInventory('read_only_user'), true);
assert.equal(canReadInventory(undefined), false);

assert.equal(canManageInventory('super_admin'), true);
assert.equal(canManageInventory('item_manager'), true);
assert.equal(canManageInventory('read_only_user'), false);
assert.equal(canManageInventory(undefined), false);

assert.equal(canAdministerSystem('super_admin'), true);
assert.equal(canAdministerSystem('item_manager'), false);
assert.equal(canAdministerSystem('read_only_user'), false);
assert.equal(canAdministerSystem(undefined), false);

// Guard against accidental role omissions when the matrix is edited later.
assert.deepEqual(roles.filter(canManageInventory), ['super_admin', 'item_manager']);
assert.deepEqual(roles.filter(canAdministerSystem), ['super_admin']);

console.log('Frontend permission contract verified.');
