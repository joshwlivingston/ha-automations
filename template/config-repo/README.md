# ha-automations config

Private config for [ha-automations](https://github.com/OWNER/ha-automations).
Keep this repo **private**: `apps.yaml` holds your entity IDs.

1. Copy this directory into a new private repo.
2. Replace `OWNER` in `.github/workflows/deploy.yml` with the owner of
   ha-automations, or your fork.
3. Edit `apps.yaml` with your entities.
4. On this repo: register a self-hosted runner (see the ha-automations README),
   then create environment `haos` with variable `HA_SSH=root@<ha-ip>`.

No tokens or secrets are needed. Deploys happen when:
- a new `v*` tag appears on ha-automations. A check runs every 15 minutes from
  06:00 to 21:00 Mountain Standard Time and hourly overnight. Edit the cron
  lines for your timezone. It does nothing if the box already
  runs the latest tag,
- you push to `main` here (the latest tag gets redeployed with the new config),
- you run the workflow manually with a tag.

To roll back, run the workflow with the old tag and disable it (Actions → Deploy →
Disable workflow). Otherwise the next check rolls forward again, within an hour at most.
The better fix is usually to release a new patch tag.
