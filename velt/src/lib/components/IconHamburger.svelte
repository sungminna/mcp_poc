<script lang="ts">
  export let size: number | string = 24;
  export let color: string = 'currentColor';
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 24 24"
  fill="none"
  stroke="{color}"
  width="{size}"
  height="{size}"
>
  <path
    stroke-linecap="round"
    stroke-linejoin="round"
    stroke-width="2"
    d="M4 6h16M4 12h16M4 18h16"
  />
</svg> 