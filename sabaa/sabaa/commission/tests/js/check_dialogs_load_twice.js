// Regression check for Critical 1: the dialogs file must survive being executed twice as a classic script.
const fs = require("fs"), vm = require("vm");
const code = fs.readFileSync(process.argv[2], "utf8");
const context = vm.createContext({ window: {}, frappe: { utils: {} }, __: (s) => s, $: () => {}, moment: () => {} });
context.window = context;
vm.runInContext(code, context, { filename: "first" });
vm.runInContext(code, context, { filename: "second" });
if (typeof context.sabaa_commission.people_dialog !== "function") throw new Error("people_dialog missing");
console.log("ok: loads twice");
