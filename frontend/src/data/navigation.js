/** Every navigation menu in one place, so the header, footer and sidebar never disagree. */

export const publicNav = [
  {
    label: 'Find Care',
    items: [
      { to: '/find-care/facilities', label: 'Healthcare facilities', note: 'Search by service, county, hours and insurer' },
      { to: '/find-care/specialists', label: 'Specialists & practitioners', note: 'Doctors, midwives, counsellors and more' },
      { to: '/find-care/laboratories', label: 'Laboratories & tests', note: 'Diagnostic tests, turnaround and home collection' },
      { to: '/find-care/insurance', label: 'Care by insurer', note: 'Facilities that report accepting your cover' },
      { to: '/find-care/map', label: 'Map of facilities', note: 'Browse facilities near a place' },
      { to: '/compare', label: 'Care Decision Assistant', note: 'Review details and questions to ask' },
    ],
  },
  {
    label: 'Health & Community',
    items: [
      { to: '/health-community/programmes', label: 'Community Programmes & Affordable Care', note: 'Screening, outreach and subsidised care' },
      { to: '/health-community/alerts', label: 'Public health alerts', note: 'Dated updates from official sources' },
      { to: '/health-library', label: 'Health library', note: 'Clear guides on reproductive health' },
      { to: '/assistant', label: 'Health assistant', note: 'General answers in English or Kiswahili' },
      { to: '/patient-experiences', label: 'Patient experiences', note: 'What patients report, with sources' },
    ],
  },
  {
    label: 'About ReproCare',
    items: [
      { to: '/about', label: 'About us', note: 'Who we are and who we serve' },
      { to: '/how-it-works', label: 'How it works', note: 'From a search to a request' },
      { to: '/trust', label: 'Our approach to trust', note: 'How we label every source' },
      { to: '/contact', label: 'Contact us', note: 'Questions, corrections and feedback' },
    ],
  },
];

export const footerNav = [
  {
    heading: 'Find care',
    links: [
      { to: '/find-care/facilities', label: 'Healthcare facilities' },
      { to: '/find-care/specialists', label: 'Specialists' },
      { to: '/find-care/laboratories', label: 'Laboratories' },
      { to: '/find-care/insurance', label: 'Care by insurer' },
      { to: '/find-care/map', label: 'Facility map' },
    ],
  },
  {
    heading: 'Health & community',
    links: [
      { to: '/health-community/programmes', label: 'Programmes & affordable care' },
      { to: '/health-community/alerts', label: 'Public health alerts' },
      { to: '/health-library', label: 'Health library' },
      { to: '/assistant', label: 'Health assistant' },
      { to: '/patient-experiences', label: 'Patient experiences' },
    ],
  },
  {
    heading: 'ReproCare',
    links: [
      { to: '/about', label: 'About us' },
      { to: '/how-it-works', label: 'How it works' },
      { to: '/trust', label: 'Our approach to trust' },
      { to: '/contact', label: 'Contact us' },
    ],
  },
  {
    heading: 'Your information',
    links: [
      { to: '/privacy', label: 'Privacy notice' },
      { to: '/terms', label: 'Terms of use' },
      { to: '/contact?topic=listing_correction', label: 'Report a listing error' },
      { to: '/contact?topic=privacy', label: 'Data requests' },
    ],
  },
];

/** Sidebar entries per role. `end` marks links that should only be active on an exact match. */
export const dashboardNav = {
  patient: [
    { to: '/dashboard', label: 'Overview', icon: 'home', end: true },
    { to: '/dashboard/appointments', label: 'Appointment requests', icon: 'calendar' },
    { to: '/dashboard/saved', label: 'Saved facilities', icon: 'heart' },
    { to: '/dashboard/registrations', label: 'Programme registrations', icon: 'ticket' },
    { to: '/dashboard/reviews', label: 'My reviews', icon: 'star' },
    { to: '/dashboard/notifications', label: 'Notifications', icon: 'bell', badge: 'unread' },
    { to: '/dashboard/account', label: 'Account settings', icon: 'settings' },
  ],
  facility_staff: [
    { to: '/dashboard/facility', label: 'Overview', icon: 'home', end: true },
    { to: '/dashboard/facility/appointments', label: 'Appointment requests', icon: 'calendar' },
    { to: '/dashboard/facility/profile', label: 'Facility profile', icon: 'building' },
    { to: '/dashboard/facility/reviews', label: 'Patient reviews', icon: 'star' },
    { to: '/dashboard/notifications', label: 'Notifications', icon: 'bell', badge: 'unread' },
    { to: '/dashboard/account', label: 'Account settings', icon: 'settings' },
  ],
  admin: [
    { to: '/dashboard/admin', label: 'Overview', icon: 'home', end: true },
    { to: '/dashboard/admin/reviews', label: 'Review moderation', icon: 'star' },
    { to: '/dashboard/admin/facebook-feedback', label: 'Facebook feedback', icon: 'star' },
    { to: '/dashboard/admin/programmes', label: 'Community programmes', icon: 'megaphone' },
    { to: '/dashboard/admin/messages', label: 'Contact messages', icon: 'inbox' },
    { to: '/dashboard/admin/users', label: 'Accounts', icon: 'users' },
    { to: '/dashboard/admin/imports', label: 'Data imports', icon: 'database' },
    { to: '/dashboard/notifications', label: 'Notifications', icon: 'bell', badge: 'unread' },
    { to: '/dashboard/account', label: 'Account settings', icon: 'settings' },
  ],
};

export const roleLabels = { patient: 'Patient', facility_staff: 'Facility staff', admin: 'Platform administrator' };
