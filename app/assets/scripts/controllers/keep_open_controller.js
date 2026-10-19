import { Controller } from "@hotwired/stimulus"

export default class KeepOpenController extends Controller {
	keep(event) {
		if (event.target == this.element && event.detail.attributeName == "open") {
			event.preventDefault()
		}
	}
}
