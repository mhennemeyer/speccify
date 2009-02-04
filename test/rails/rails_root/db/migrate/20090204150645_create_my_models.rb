class CreateMyModels < ActiveRecord::Migration
  def self.up
    create_table :my_models do |t|
      t.string :title

      t.timestamps
    end
  end

  def self.down
    drop_table :my_models
  end
end
