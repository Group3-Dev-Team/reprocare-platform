import { expect, it } from 'vitest';
import { isFacilityPhone, isKenyanPhone } from '../data/phone';

it('accepts Kenyan mobile and landline numbers in local and international form', () => {
  for (const ok of ['0712345678', '0712 345 678', '+254 712-345-678', '254712345678', '0110 123 456', '020 272 2541', '(041) 222 3344']) {
    expect(isKenyanPhone(ok)).toBe(true);
  }
});

it('refuses letters and malformed numbers', () => {
  for (const bad of ['shgihcwsbdcjebdc', '07123', '071234567890', '+1 202 555 0101', '0712abc678', '', '++254712345678']) {
    expect(isKenyanPhone(bad)).toBe(false);
  }
});

it('lets facility contact fields hold several or international numbers but no text', () => {
  expect(isFacilityPhone('+254 20 2722541, 0722 123 456')).toBe(true);
  expect(isFacilityPhone('+44 20 7946 0958')).toBe(true);
  expect(isFacilityPhone('')).toBe(true);
  expect(isFacilityPhone('call reception')).toBe(false);
});
