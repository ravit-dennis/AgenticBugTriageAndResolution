# Demonstration Scenarios

The repository keeps a correct baseline and provides repeatable patches that introduce the two required bugs.

## Backend pagination bug

```powershell
git apply demo\bugs\backend-pagination.patch
Set-Location target-app
npm test -- --run backend/helper/pagination.test.js
```

The seeded bug multiplies the API `offset` by `limit`, so an offset of 20 with a limit of 10 skips 200 records. The regression test passes on the baseline and fails after the patch.

Reset the scenario:

```powershell
Set-Location ..
git apply --reverse demo\bugs\backend-pagination.patch
```

The matching offline issue event is `demo\events\backend-pagination-bug.json`.

## Frontend settings retry bug

```powershell
git apply demo\bugs\frontend-settings.patch
Set-Location target-app
npm test -- --run frontend/src/components/SettingsForm/SettingsForm.test.jsx
```

The seeded bug leaves the form inactive after a rejected update request, so the submit button does not return and the user cannot retry. The regression test passes on the baseline and fails after the patch.

Reset the scenario:

```powershell
Set-Location ..
git apply --reverse demo\bugs\frontend-settings.patch
```

The matching offline issue event is `demo\events\frontend-settings-bug.json`.

Apply and reset one scenario at a time. Each agent run should persist the exact failing reproduction command and rerun it unchanged after the repair.
