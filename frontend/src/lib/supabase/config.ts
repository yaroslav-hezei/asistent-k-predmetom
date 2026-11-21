// Supabase is used only to log in; all data comes from our API. Both values are public (they end up
// in the browser) and are read at build time. Without them the app runs, but nobody can log in.
export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
export const authConfigured = Boolean(supabaseUrl && supabaseKey);
