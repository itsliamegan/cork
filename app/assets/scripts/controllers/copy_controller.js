export default class extends Stimulus.Controller {
	static targets = ["source", "button"]

	connect() {
		if (this.sourceTarget.href) {
			this.sourceTarget.textContent = this.sourceTarget.href
		}
	}

	async copy() {
		let value = this.sourceTarget.href ?? this.sourceTarget.textContent.trim()
		await navigator.clipboard.writeText(value)

		let range = document.createRange()
		range.selectNodeContents(this.sourceTarget)
		let selection = window.getSelection()
		selection.removeAllRanges()
		selection.addRange(range)

		if (this.hasButtonTarget) {
			this.buttonTarget.textContent = "Copied"
		}
	}
}
