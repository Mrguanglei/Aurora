export const siteConfig = {
  url: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  nav: {
    links: [
      { id: 1, name: 'Home', href: '#hero' },
      { id: 2, name: 'Process', href: '#process' },
      { id: 4, name: 'Open Source', href: '#open-source' },
      { id: 5, name: 'Pricing', href: '#pricing' },
      { id: 6, name: 'Enterprise', href: '/enterprise' },
    ],
  },
  hero: {
    description:
      'Kortix – open-source platform to build, manage and train your AI Workforce.',
  },
  cloudPricingItems: [],
  footerLinks: [
    {
      title: 'Kortix',
      links: [
        { id: 1, title: 'About', url: '' },
        { id: 3, title: 'Contact', url: '' },
        { id: 4, title: 'Careers', url: '' },
      ],
    },
    {
      title: 'Resources',
      links: [
        {
          id: 5,
          title: 'Documentation',
          url: '',
        },
        { id: 7, title: 'Discord', url: '' },
        { id: 8, title: 'GitHub', url: '' },
      ],
    },
    {
      title: 'Legal',
      links: [
        {
          id: 9,
          title: 'Privacy Policy',
          url: '',
        },
        {
          id: 10,
          title: 'Terms of Service',
          url: '',
        },
        {
          id: 11,
          title: 'License',
          url: '',
        },
      ],
    },
  ],
};

export type SiteConfig = typeof siteConfig;
