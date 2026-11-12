const PRE_ORDER_WORKFLOW = "Sales Pre-Order";
const CANCEL_ACTION = "Cancel";

frappe.ui.form.on("Sales Order", {
	before_workflow_action(frm) {
		const workflow = frappe.workflow.workflows[frm.doctype];
		const is_pre_order_cancel =
			workflow?.name === PRE_ORDER_WORKFLOW &&
			frm.selected_workflow_action === CANCEL_ACTION;

		if (!is_pre_order_cancel) return;

		return confirm_pre_order_cancel(frm);
	},
});

function confirm_pre_order_cancel(frm) {
	// Frappe freezes the screen before this event; lift it so the dialog is usable.
	frappe.dom.unfreeze();

	// On "No" the promise stays pending, so Frappe never applies the action
	// and no unhandled rejection is logged.
	return new Promise((resolve) => {
		frappe.confirm(
			__("Are you sure you want to cancel Sales Order {0}?", [
				frappe.utils.escape_html(frm.doc.name).bold(),
			]),
			() => {
				// Frappe unfreezes once after the action call finishes.
				frappe.dom.freeze();
				resolve();
			}
		);
	});
}
