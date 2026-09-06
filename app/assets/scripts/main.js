import BoardOrderController from "./controllers/board_order_controller.js"

Turbo.config.drive.progressBarDelay = 250
Turbo.start()

let application = Stimulus.Application.start()
application.register("board-order", BoardOrderController)
