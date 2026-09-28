export default class KeepOpenController extends Stimulus.Controller {
	keep(event) {
		if (event.target == this.element && event.detail.attributeName == "open") {
			event.preventDefault()
		}
	}
}
