import CopyController from "./controllers/copy_controller.js"
import FilterController from "./controllers/filter_controller.js"
import PinDetailsController from "./controllers/pin_details_controller.js"
import ReorderController from "./controllers/reorder_controller.js"

Turbo.config.drive.progressBarDelay = 250
Turbo.start()

let application = Stimulus.Application.start()
application.register("copy", CopyController)
application.register("filter", FilterController)
application.register("pin-details", PinDetailsController)
application.register("reorder", ReorderController)
