# Free Daily Instagram Auto-Poster

Every day GitHub Actions runs `post.py`, which publishes the next unposted image from `posts.json` to your Instagram page, then marks it as posted. Cost: $0.

## One-time setup

### 1. Instagram account
- Switch your Instagram to a **Business** or **Creator** account (Settings > Account type).
- Link it to a **Facebook Page** (Instagram > Settings > Accounts Center, or Page settings > Linked accounts).

### 2. Meta developer app (free)
1. In your app: **Use cases > Customize > API setup with Facebook login**. Click **Add required content permissions**.
2. Open **Tools > Graph API Explorer**, select your app, click **Generate Access Token**, and allow: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`.
3. Make it last about 60 days: **Tools > Access Token Debugger**, paste the token, click **Debug**, then **Extend Access Token**. This is `IG_ACCESS_TOKEN`.
4. Get `IG_USER_ID`: in Graph API Explorer run `me/accounts` (copy your Page `id`), then run `PAGE_ID?fields=instagram_business_account` and copy the `id` inside it.

> While your app is in Development mode, it works for your own account without app review.

### 3. GitHub repo
1. Create a **public** repo (images must be reachable by Instagram via a public URL) and upload all these files, keeping the folder layout.
2. Add your images in an `images/` folder (JPG, ideally 1080x1080 or 1080x1350).
3. Repo > **Settings > Secrets and variables > Actions** > add:
   - `IG_USER_ID`
   - `IG_ACCESS_TOKEN`
4. Go to the **Actions** tab, open "Daily Instagram Post", click **Run workflow** to test.

## Daily use
Add new entries to `posts.json` (image path + caption) whenever you like. Queue up weeks at once. When the queue is empty the job does nothing.

## Things to know
- **Token expires about every 60 days.** Set a calendar reminder to generate a new one and update the `IG_ACCESS_TOKEN` secret.
- Instagram limits API posts to about 100 per day, far above what you need.
- Change the time by editing the `cron` line in `.github/workflows/daily-post.yml` (it uses UTC).
- GitHub may delay scheduled runs by several minutes, and disables schedules on repos with no activity for 60 days. The post commits keep it active.
- For a private repo, host images elsewhere (e.g. Cloudinary free tier) and put full URLs in the `image` field. This needs a one-line change in `post.py`.
