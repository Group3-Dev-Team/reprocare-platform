// Telephone checks matching backend/app/services/phone.py. The server validates again.
const SEPARATORS = /[\s().-]/g;
const KENYAN = /^(?:\+?254|0)[1-9]\d{8}$/;
const INTERNATIONAL = /^\+[1-9]\d{7,14}$/;

export const PHONE_MESSAGE = 'Enter a Kenyan phone number, for example 0712 345 678 or +254 712 345 678.';
export const FACILITY_PHONE_MESSAGE = 'Enter phone numbers using digits only, for example 020 272 2541 or +254 712 345 678; separate several with commas.';

/** Kenyan mobile or landline in 07…/01…/02…, 254… or +254… form, with optional spaces, dots, dashes or brackets. */
export function isKenyanPhone(value) {
  return KENYAN.test(String(value || '').replace(SEPARATORS, ''));
}

/** One or more Kenyan or international numbers (a facility's public contact field); empty is allowed. */
export function isFacilityPhone(value) {
  const text = String(value || '').trim();
  if (!text) return true;
  return text.split(/\s*(?:[;,/]|\bor\b)\s*/i).filter(Boolean)
    .every((part) => { const c = part.replace(SEPARATORS, ''); return KENYAN.test(c) || INTERNATIONAL.test(c); });
}
