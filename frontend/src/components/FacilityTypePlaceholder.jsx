import { Baby, Building2, FlaskConical, HeartPulse, Stethoscope } from 'lucide-react';

const facilityTypeIcons = {
  hospital: Building2,
  clinic: Stethoscope,
  maternity_home: Baby,
  health_centre: HeartPulse,
  laboratory: FlaskConical,
};

export function FacilityTypePlaceholder({ type, size }) {
  const Icon = facilityTypeIcons[type] ?? Building2;
  return <Icon size={size} aria-hidden="true" />;
}
