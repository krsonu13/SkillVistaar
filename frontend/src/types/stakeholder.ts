import { AccountType } from './auth';

export interface StakeholderFeature {
  title: string;
  description: string;
  metric?: string;
  metricLabel?: string;
}

export interface StakeholderSectionData {
  id: AccountType;
  title: string;
  badge: string;
  subtitle: string;
  description: string;
  highlights: string[];
  metrics: { value: string; label: string }[];
  primaryCtaText: string;
  primaryCtaLink: string;
  secondaryCtaText: string;
  secondaryCtaLink: string;
}
