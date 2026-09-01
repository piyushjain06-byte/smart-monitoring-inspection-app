// Keep in sync with apps/core/permissions.py (OFFICIAL_ROLES / FIELD_ROLES)
export const OFFICIAL_ROLES = ["SUPER_ADMIN", "STATE_AUTHORITY", "DISTRICT_AUTHORITY"];
export const FIELD_ROLES = ["INSPECTION_OFFICER", "PMU_TEAM"];

export function isOfficial(user) {
  if (!user) return false;
  return user.is_staff || user.is_superuser || OFFICIAL_ROLES.includes(user.role);
}

export function isFieldOfficer(user) {
  if (!user) return false;
  return FIELD_ROLES.includes(user.role) && !isOfficial(user);
}
