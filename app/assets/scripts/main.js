Turbo.config.drive.progressBarDelay = 250
Turbo.start()

class MenuController extends Stimulus.Controller {
	static targets = ["button", "items"]
	static classes = ["open"]

	initialize() {
		this.isOpen = false
		document.addEventListener("click", this.onDocumentClick.bind(this))
		document.addEventListener("turbo:before-cache", this.onBeforeCache.bind(this))
	}

	toggle() {
		if (this.isOpen) {
			this.close()
		} else {
			this.open()
		}
	}

	open() {
		this.isOpen = true
		this.itemsTarget.classList.add(this.openClass)
	}

	close() {
		this.isOpen = false
		this.itemsTarget.classList.remove(this.openClass)
	}

	onDocumentClick(event) {
		if (this.isOpen && event.target !== this.buttonTarget) {
			this.close()
		}
	}

	onBeforeCache() {
		this.close()
	}
}

let application = Stimulus.Application.start()
application.register("menu", MenuController)
