const DELAY = 5000
const DURATION = 400

export default class extends Stimulus.Controller {
	connect() {
		this.timeout = setTimeout(() => this.fade(), DELAY)
	}

	disconnect() {
		clearTimeout(this.timeout)
	}

	async fade() {
		let animation = this.element.animate([{ opacity: 1 }, { opacity: 0 }], {
			duration: DURATION,
			easing: "ease-out",
			fill: "forwards",
		})
		await animation.finished
		this.element.remove()
	}
}
