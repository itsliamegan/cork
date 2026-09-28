import CopyController from "./controllers/copy_controller.js"
import FilterController from "./controllers/filter_controller.js"
import KeepOpenController from "./controllers/keep_open_controller.js"
import NoticeController from "./controllers/notice_controller.js"
import PinDetailsController from "./controllers/pin_details_controller.js"
import ReorderController from "./controllers/reorder_controller.js"

Turbo.config.drive.progressBarDelay = 250
Turbo.start()

let application = Stimulus.Application.start()
application.register("copy", CopyController)
application.register("filter", FilterController)
application.register("keep-open", KeepOpenController)
application.register("notice", NoticeController)
application.register("pin-details", PinDetailsController)
application.register("reorder", ReorderController)
