import BoardOrderController from "./controllers/board_order_controller.js"
import CopyController from "./controllers/copy_controller.js"
import FilterController from "./controllers/filter_controller.js"

Turbo.config.drive.progressBarDelay = 250
Turbo.start()

let application = Stimulus.Application.start()
application.register("board-order", BoardOrderController)
application.register("copy", CopyController)
application.register("filter", FilterController)
