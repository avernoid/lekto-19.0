# **FSM Skip Wizard On Sale**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This module adds a **per-project toggle** to Odoo 19 Field Service that automatically bypasses the stop-timer confirmation wizard when a **confirmed Sale Order** is linked to the task. When the bypass is active, time is logged instantly with the description **"Automated register"** — eliminating unnecessary clicks for your field technicians.

If no confirmed sale order exists (or the toggle is disabled), the native Odoo confirmation wizard opens normally. Zero disruption to existing workflows.

---

## Why This Module?

In field service operations, when a technician completes a task that already has a confirmed customer order, the stop-timer confirmation dialog adds zero business value. This module eliminates that friction while preserving full control:

| Condition | Result |
|---|---|
| Toggle enabled + Confirmed SO | ✅ Auto-register time, skip wizard |
| Toggle enabled + No/Draft SO | 🔔 Native wizard opens normally |
| Toggle disabled | 🔔 Native wizard always opens |

---

## Requirements

- Odoo 19 Enterprise (Odoo.SH, Ganemo Online, or Ganemo.SH)
- Modules: `industry_fsm`, `industry_fsm_sale`
- **Not** compatible with Odoo Online (custom code restrictions)

---

## Installation

1. Copy `fsm_skip_wizard_on_sale` into your Odoo addons path.
2. Update the module list (`Settings > Technical > Update Module List`).
3. Install **FSM Skip Wizard On Sale** from the apps list.

> If you also use `fsm_geofencing_control`, it will automatically depend on this module. Install both for GPS + auto-time-logging together.

---

## Configuration

1. Go to **Field Service** → open an FSM Project.
2. Navigate to the **Field Service** settings tab (visible when `allow_material` is enabled, i.e., the project allows using materials/products).
3. Enable **"Skip Wizard If Sale Exists"**.
4. Save.

The setting is project-scoped — each project can independently enable or disable the bypass.

---

## How It Works

### Stop Timer Flow (Bypass Active)

```
Technician clicks [Stop] on FSM task
    ↓
Does the task's project have skip_wizard_on_sale = True?
    ↓ YES
Does the task have a Sale Order in 'sale' or 'done' state?
    ↓ YES
Compute elapsed time (using native Odoo rounding rules)
Write timesheet name = "Automated register"
Return False → No wizard opens
UI reloads the form automatically
```

### Stop Timer Flow (Normal)

```
Technician clicks [Stop] on FSM task
    ↓
Condition NOT met (toggle off, or no confirmed SO)
    ↓
Native confirmation wizard opens (standard Odoo behavior)
```

---

## Compatibility with fsm_geofencing_control

This module is designed as **Layer 2** in the FSM extension stack:

```
Layer 1: industry_fsm + industry_fsm_sale     (Odoo native)
Layer 2: fsm_skip_wizard_on_sale              ← This module (standalone)
Layer 3: fsm_geofencing_control               depends on Layer 2
```

The Method Resolution Order ensures:
`geofencing → skip_wizard → industry_fsm → Odoo base`

When geofencing is also installed, GPS validation runs first. If the bypass is triggered, time is logged automatically and geofencing's lost-reason logic is also bypassed (since by definition a confirmed sale means the task was not lost).

---

## Fields

### `project.project`

| Field | Label | Description |
|---|---|---|
| `skip_wizard_on_sale` | Skip Wizard If Sale Exists | When enabled, the stop-timer confirmation wizard is bypassed if the task has a confirmed Sale Order. Time is logged automatically as "Automated register". |

---

## QA / Testing Scenarios

### Scenario 1 — Bypass Activated
1. Enable **"Skip Wizard If Sale Exists"** on an FSM project.
2. Create a task linked to a **confirmed** Sale Order.
3. Start the timer. Wait a few seconds. Click **Stop**.
4. ✅ Wizard does NOT appear. Timesheet shows `"Automated register"` with computed time.

### Scenario 2 — No Sale: Wizard Opens Normally
1. Same project with toggle enabled.
2. Task with **no Sale Order** (or draft SO).
3. Start and stop timer.
4. ✅ Native confirmation wizard opens as expected.

### Scenario 3 — Toggle Disabled
1. Disable the toggle on the project.
2. Task with confirmed SO. Start and stop timer.
3. ✅ Wizard opens normally — toggle fully guards the behaviour.

### Scenario 4 — Coexistence with Geofencing
1. Install `fsm_skip_wizard_on_sale` + `fsm_geofencing_control`.
2. Enable both GPS control and skip wizard toggle on the project.
3. Stop timer from a valid GPS location with a confirmed SO.
4. ✅ Time auto-logged. GPS validation runs, wizard is skipped.

---

## FAQ

**Q: The wizard still appears even with a confirmed SO. Why?**
A: Check two things: (1) Is the toggle enabled on the project? (2) Is the SO status `confirmed` or `done`? Draft and cancelled SOs do NOT trigger the bypass.

**Q: Can I use this without fsm_geofencing_control?**
A: Yes! This module is 100% standalone.

**Q: What description is written to the timesheet?**
A: `"Automated register"` (English) / `"Registro automatizado"` (Spanish).

**Q: Is the time calculation accurate?**
A: Yes. Odoo's native rounding logic is called first, so the elapsed time computed is identical to what you would see in the manual wizard.

**Q: Can I prevent this bypass for specific projects?**
A: Yes — just leave the toggle disabled on those projects. The wizard opens normally.

---

## Languages

| Language | Status |
|---|---|
| English (en_US) | ✅ Native |
| Spanish (es_ES / es_PE / es_MX) | ✅ Included |

---

## Author

**Author**: [Ganemo](https://www.ganemo.co)
**Maintainer**: Ganemo
**License**: OPL-1 — Odoo Proprietary License v1.0
**Price**: $35 USD
**Version**: 19.0.1.0.0

---

## Support

| Channel | Contact |
|---|---|
| 💬 WhatsApp (Sales) | [+1 (828) 672-6150](https://wa.me/18286726150) |
| 📧 Sales Email | [leads@ganemo.com](mailto:leads@ganemo.com) |
| 🛠 Technical Support | [help@ganemo.com](mailto:help@ganemo.com) |
| 📅 Book a Demo | [ganemo.co/appointment/5](https://www.ganemo.co/appointment/5) |
