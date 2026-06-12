import * as React from "react"
import { cn } from "@/lib/utils"

interface TabsContextValue {
  activeTab: string
  setActiveTab: (value: string) => void
}

const TabsContext = React.createContext<TabsContextValue | undefined>(undefined)

interface TabsProps {
  defaultValue: string
  children: React.ReactNode
  className?: string
}

export function Tabs({ defaultValue, children, className }: TabsProps) {
  const [activeTab, setActiveTab] = React.useState(defaultValue)

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

interface TabsListProps {
  children: React.ReactNode
  className?: string
}

export function TabsList({ children, className }: TabsListProps) {
  return (
    <div
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-lg p-1",
        "bg-elevated border border-default",
        className
      )}
    >
      {children}
    </div>
  )
}

interface TabsTriggerProps {
  value: string
  children: React.ReactNode
  className?: string
}

export function TabsTrigger({ value, children, className }: TabsTriggerProps) {
  const context = React.useContext(TabsContext)
  if (!context) throw new Error("TabsTrigger must be used within Tabs")

  const { activeTab, setActiveTab } = context
  const isActive = activeTab === value

  return (
    <button
      type="button"
      onClick={() => setActiveTab(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-all",
        isActive
          ? "bg-surface text-primary shadow-sm dark:shadow-none dark:ring-1 dark:ring-border-strong"
          : "text-muted hover:text-primary",
        className
      )}
    >
      {children}
    </button>
  )
}

interface TabsContentProps {
  value: string
  children: React.ReactNode
  className?: string
  /**
   * Keep the panel mounted once it has been activated, hiding it (display:none)
   * when inactive instead of unmounting. Preserves local state (filters, scroll)
   * and avoids re-running data fetches on every tab switch. Mounts lazily on
   * first activation, so panels whose children fetch on mount don't all fire
   * up front.
   */
  keepAlive?: boolean
}

export function TabsContent({ value, children, className, keepAlive }: TabsContentProps) {
  const context = React.useContext(TabsContext)
  if (!context) throw new Error("TabsContent must be used within Tabs")

  const { activeTab } = context
  const isActive = activeTab === value

  // Track whether this panel has ever been the active tab (only relevant when
  // keepAlive is set). Conditionally updating state during render is the
  // documented React pattern for deriving state from props without an effect.
  const [hasBeenActive, setHasBeenActive] = React.useState(isActive)
  if (isActive && !hasBeenActive) setHasBeenActive(true)

  if (!keepAlive) {
    if (!isActive) return null
    return <div className={cn("mt-4 animate-fade-in", className)}>{children}</div>
  }

  if (!hasBeenActive) return null
  return (
    <div className={cn("mt-4", isActive && "animate-fade-in", className)} hidden={!isActive}>
      {children}
    </div>
  )
}
