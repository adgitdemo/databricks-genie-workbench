import React, {type ReactNode} from 'react';
import {useWindowSize} from '@docusaurus/theme-common';
import {
  useLockBodyScroll,
  useNavbarMobileSidebar,
} from '@docusaurus/theme-common/internal';
import NavbarMobileSidebarLayout from '@theme/Navbar/MobileSidebar/Layout';
import NavbarMobileSidebarHeader from '@theme/Navbar/MobileSidebar/Header';
import NavbarMobileSidebarPrimaryMenu from '@theme/Navbar/MobileSidebar/PrimaryMenu';
import NavbarMobileSidebarSecondaryMenu from '@theme/Navbar/MobileSidebar/SecondaryMenu';

// Swizzled to raise the navbar collapse breakpoint. Docusaurus hardcodes 996px
// in both JS and CSS (facebook/docusaurus#9603, no config option). Here we gate
// the drawer on a custom breakpoint; the matching CSS lives in custom.css under
// the same value. `shown`/`toggle` still come from the shared context, so the
// hamburger keeps working in the widened range. Keep this value in sync with
// the --collapse media queries in custom.css.
const COLLAPSE_BREAKPOINT = 1140;

export default function NavbarMobileSidebar(): ReactNode {
  const mobileSidebar = useNavbarMobileSidebar();
  const windowSize = useWindowSize({desktopBreakpoint: COLLAPSE_BREAKPOINT});
  useLockBodyScroll(mobileSidebar.shown);
  // Render the drawer whenever we're below the (raised) breakpoint.
  if (windowSize !== 'mobile') {
    return null;
  }
  return (
    <NavbarMobileSidebarLayout
      header={<NavbarMobileSidebarHeader />}
      primaryMenu={<NavbarMobileSidebarPrimaryMenu />}
      secondaryMenu={<NavbarMobileSidebarSecondaryMenu />}
    />
  );
}
