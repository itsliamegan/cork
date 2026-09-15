export default class extends Stimulus.Controller {
	static targets = ["link", "frame"]

	toggle(event) {
		if (this.element.classList.contains("pin-row--expanded")) {
			event.preventDefault()
			this.frameTarget.remove()
			this.element.classList.remove("pin-row--expanded")
			this.linkTarget.textContent = "Details"
			return
		}

		this.ensureFrame()
		this.element.classList.add("pin-row--expanded")
		this.linkTarget.textContent = "Hide details"
	}

	ensureFrame() {
		if (this.hasFrameTarget) return

		let frame = document.createElement("turbo-frame")
		frame.id = this.linkTarget.dataset.turboFrame
		frame.dataset.pinDetailsTarget = "frame"
		this.element.append(frame)
	}
}
