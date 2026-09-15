export default class extends Stimulus.Controller {
	static targets = ["query", "item", "empty"]

	connect() {
		this.filter()
	}

	filter() {
		let query = this.queryTarget.value.trim().toLocaleLowerCase()
		let visibleItems = 0

		for (let item of this.itemTargets) {
			let searchableText = item.dataset.filterText.toLocaleLowerCase()
			let matches = searchableText.includes(query)
			item.hidden = !matches
			if (matches) {
				visibleItems += 1
			}
		}
		this.emptyTarget.hidden = query.length === 0 || visibleItems > 0
	}
}
