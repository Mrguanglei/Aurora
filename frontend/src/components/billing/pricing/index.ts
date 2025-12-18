/**
 * 账单系统已删除（私有化部署）
 * 本文件保留用于向后兼容性。
 */

// 保留原先的弹窗组件签名
export const PlanSelectionModal = (_props: any) => null;

// 计费页面组件，彻底通过 any 避开所有 props 的类型检查
export const PricingSection = (_props: any) => null;
