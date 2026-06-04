import React from 'react';
import {useThemeConfig} from '@docusaurus/theme-common';
import {useNavbarMobileSidebar} from '@docusaurus/theme-common/internal';
import NavbarItem from '@theme/NavbarItem';
import NavbarColorModeToggle from '@theme/Navbar/ColorModeToggle';

function useNavbarItems() {
  // TODO temporary casting until ThemeConfig type is improved
  return useThemeConfig().navbar.items as any[];
}

// The primary menu displays the navbar items.
// Swizzled: append the color mode toggle after the items so it sits next to the
// GitHub icon at the bottom of the drawer (moved out of the sidebar header).
export default function NavbarMobilePrimaryMenu(): JSX.Element {
  const mobileSidebar = useNavbarMobileSidebar();
  const items = useNavbarItems();
  return (
    <ul className="menu__list">
      {items.map((item, i) => (
        <NavbarItem
          mobile
          {...item}
          onClick={() => mobileSidebar.toggle()}
          key={i}
        />
      ))}
      <li className="menu__list-item navbar-sidebar__toggle-item">
        <NavbarColorModeToggle className="margin-left--sm" />
      </li>
    </ul>
  );
}
