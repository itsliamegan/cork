export default class NoticeController extends Stimulus.Controller {
	static DELAY = 5000
	static DURATION = 400

	connect() {
		this.timeout = setTimeout(() => this.fade(), NoticeController.DELAY)
	}

	disconnect() {
		clearTimeout(this.timeout)
	}

	async fade() {
		let animation = this.element.animate([{ opacity: 1 }, { opacity: 0 }], {
			duration: NoticeController.DURATION,
			easing: "ease-out",
			fill: "forwards",
		})
		await animation.finished
		this.element.remove()
	}
}
