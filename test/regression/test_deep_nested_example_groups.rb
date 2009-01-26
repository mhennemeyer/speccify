require File.dirname(__FILE__) + "/../test_helper.rb"

describe "top level EG contains a before and deeper nested group" do
  
  before do
    @var_defined_in_top_level_e_g = "Horst"
  end

  describe "2" do
    describe "3" do
      describe "4" do
        describe "5" do
          it "should know var_defined_in_top_level_e_g" do
            @var_defined_in_top_level_e_g.should == "Horst"
          end
        end
      end
    end
  end
end