# Hosting the dashboard on Vercel

The dashboard is a static Vite site in `web/`, so Vercel can serve it on the free Hobby plan, including from a **private** GitHub repo. Raw data never ships with the site: the deployed pages hold only the aggregate JSON in `web/public/data/`, and the Data files page links to the Google Drive copy.

## 0. Make the repo private (do this first)

The instructor wants the data private. Earlier commits on GitHub still contain the four CSVs, so hide the whole repo:

1. Go to `github.com/Incognius/DPCN-A2-EigenMinds`.
2. Open **Settings → General → Danger Zone → Change repository visibility** and choose **Private**.
3. Add Manit and Shashwat as collaborators under **Settings → Collaborators**.

## 1. Deploy from GitHub (recommended, auto-redeploys on every push)

1. Sign in at <https://vercel.com> with **Continue with GitHub**.
2. Click **Add New… → Project**. Then **Import Git Repository → Adjust GitHub App Permissions**, and allow the private repo `DPCN-A2-EigenMinds`.
3. Click **Import** on `DPCN-A2-EigenMinds`.
4. Configure the project:

   | Setting | Value |
   |---|---|
   | Framework Preset | **Vite** |
   | Root Directory | **`web`** (click *Edit* and pick the folder; this matters) |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |
   | Install Command | `npm install` |
   | Node.js version (Settings → General, after the first deploy) | 22.x |

   No environment variables are needed.
5. Click **Deploy**. After about a minute you get a URL such as `https://dpcn-a2-eigenminds.vercel.app`.
6. Optional: rename the project or add a domain under **Settings → Domains**, for example `iiser-atlas-group20.vercel.app`.

The site uses hash routing (`#/citation/ALL`) and relative asset paths, so it needs no rewrites or `vercel.json`.

## 2. Alternative: deploy from your laptop with the CLI

```bash
npm install -g vercel
```

```bash
cd web && vercel --prod
```

The first run opens a browser to log in, then asks a few questions:

- **Set up and deploy?** Yes.
- **Scope:** your account.
- **Link to existing project?** No.
- **Project name:** `dpcn-a2-eigenminds`.
- **Directory:** `./`.

It detects Vite and the default settings are right. It prints the production URL.

## 3. Put the links into every deliverable

1. Upload `submission/Group20_IISER_data.zip` to Google Drive.
2. Use **Share → General access: Restricted** and add the instructor and TAs by email. "Anyone with the link" also works if the course allows it.
3. Copy the share link.
4. Edit `config/institutions.yaml`:

   ```yaml
   dashboard_url: https://dpcn-a2-eigenminds.vercel.app/
   drive_url: https://drive.google.com/file/d/<id>/view?usp=sharing
   ```

5. Rebuild the dashboard JSON, the report PDF (links and QR code) and both zips:

   ```bash
   python -m dpcn finalize
   ```

6. Commit and push. Vercel redeploys automatically, and the dashboard's Data files page now opens the Drive link.

## Troubleshooting

- **The build fails with "Cannot find module" or tsc errors.** The Root Directory is not `web`. Fix it in Settings → General and redeploy.
- **The page is blank but the build succeeded.** Check that the Output Directory is `dist`, not `web/dist`, because the root is already `web`.
- **You can't see the private repo when importing.** Grant the Vercel GitHub App access to that repo, as in step 1.2.
